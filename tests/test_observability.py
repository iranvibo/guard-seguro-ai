"""Unit and integration tests for US-07: Traceability, Observability & Reasoning Logging.

Validates intermediate step capturing, exact tool parameter logging, execution latency,
token consumption accounting, cost estimation, callback handlers, and audit report generation.
"""

import json
import time
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from langchain_core.outputs import Generation, LLMResult

from src.agent.claim_agent import ClaimEvaluatorAgent, evaluate_claim
from src.agent.observability import (
    AgentAuditorCallbackHandler,
    calculate_token_cost,
    estimate_text_tokens,
    export_audit_trail_dict,
    format_audit_log_markdown,
    format_reasoning_flow_mermaid,
)
from src.core.models import (
    ClaimAssessment,
    CostBreakdown,
    CoverageStatus,
    ExecutionMetrics,
    ToolCallTrace,
)


class TestObservabilityModels:
    """Tests for ExecutionMetrics and ToolCallTrace Pydantic schemas."""

    def test_execution_metrics_defaults(self) -> None:
        metrics = ExecutionMetrics()
        assert metrics.execution_time_seconds == 0.0
        assert metrics.prompt_tokens == 0
        assert metrics.completion_tokens == 0
        assert metrics.total_tokens == 0
        assert metrics.estimated_cost_usd == 0.0
        assert metrics.model_name == "gpt-4o-mini"
        assert metrics.tools_called == []
        assert metrics.tools_count == 0

    def test_execution_metrics_auto_sync_tokens_and_tools(self) -> None:
        metrics = ExecutionMetrics(
            prompt_tokens=150,
            completion_tokens=50,
            tools_called=["check_policy_coverage", "calculate_repair_estimate"],
        )
        assert metrics.total_tokens == 200
        assert metrics.tools_count == 2

    def test_tool_call_trace_creation(self) -> None:
        trace = ToolCallTrace(
            step_number=1,
            tool="check_policy_coverage",
            tool_input={"damage_type": "luna rota", "policy_type": "Auto"},
            observation={"is_covered": True, "standard_deductible": 0.0},
            thought="El asegurado menciona rotura de luna, procedo a verificar cobertura.",
            execution_time_seconds=0.0125,
        )
        assert trace.step_number == 1
        assert trace.tool == "check_policy_coverage"
        assert trace.tool_input["damage_type"] == "luna rota"
        assert trace.observation["is_covered"] is True
        assert "verificar cobertura" in trace.thought
        assert trace.execution_time_seconds == 0.0125
        assert isinstance(trace.timestamp, datetime)


class TestTokenAndCostEstimation:
    """Tests for token estimators and monetary cost formulas."""

    def test_estimate_text_tokens_empty(self) -> None:
        assert estimate_text_tokens("") == 0
        assert estimate_text_tokens("   ") == 0

    def test_estimate_text_tokens_non_empty(self) -> None:
        # 38 chars ~ 10 tokens
        sample = "Este es un texto de prueba para tokens"
        tokens = estimate_text_tokens(sample)
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_calculate_token_cost_gpt4o_mini(self) -> None:
        # 1M prompt tokens ($0.15) + 1M completion tokens ($0.60) = $0.75
        cost = calculate_token_cost(
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            model_name="gpt-4o-mini",
        )
        assert cost == 0.75

    def test_calculate_token_cost_small_usage(self) -> None:
        cost = calculate_token_cost(
            prompt_tokens=1000,
            completion_tokens=300,
            model_name="gpt-4o-mini",
        )
        assert cost > 0.0
        assert cost < 0.01


class TestAgentAuditorCallbackHandler:
    """Tests for the LangChain auditing callback handler."""

    def test_callback_lifecycle_tracking(self) -> None:
        handler = AgentAuditorCallbackHandler(model_name="gpt-4o-mini")

        # 1. Chain start
        handler.on_chain_start(serialized={}, inputs={"claim_text": "Golpe en aleta"})
        assert handler.start_time is not None

        # 2. LLM start
        handler.on_llm_start(
            serialized={},
            prompts=["Eres un evaluador de siniestros de Allianz Spain."],
        )
        assert handler.prompt_tokens > 0

        # 3. Agent action (thought log)
        mock_action = MagicMock()
        mock_action.log = "Comprobando cobertura de chapa y pintura..."
        handler.on_agent_action(mock_action)
        assert handler._latest_agent_thought == "Comprobando cobertura de chapa y pintura..."

        # 4. Tool start and end
        handler.on_tool_start(
            serialized={"name": "check_policy_coverage"},
            input_str="chapa golpeada",
            input={"damage_type": "chapa", "policy_type": "Auto"},
        )
        time.sleep(0.005)
        handler.on_tool_end(
            output=json.dumps({"cubierto": True, "franquicia_estandar": 150.0}),
            input={"damage_type": "chapa", "policy_type": "Auto"},
        )

        assert len(handler.tool_calls_trace) == 1
        trace = handler.tool_calls_trace[0]
        assert trace.step_number == 1
        assert trace.tool == "check_policy_coverage"
        assert trace.tool_input == {"damage_type": "chapa", "policy_type": "Auto"}
        assert trace.observation == {"cubierto": True, "franquicia_estandar": 150.0}
        assert trace.thought == "Comprobando cobertura de chapa y pintura..."
        assert trace.execution_time_seconds is not None and trace.execution_time_seconds > 0

        # 5. LLM end with explicit token_usage
        llm_result = LLMResult(
            generations=[[Generation(text='{"status": "Aprobado"}')]],
            llm_output={"token_usage": {"prompt_tokens": 250, "completion_tokens": 60, "total_tokens": 310}},
        )
        handler.on_llm_end(llm_result)
        assert handler.prompt_tokens == 250
        assert handler.completion_tokens == 60
        assert handler.total_tokens == 310

        # 6. Chain end
        handler.on_chain_end(outputs={"output": '{"status": "Aprobado"}'})
        assert handler.end_time is not None

        # 7. Validate generated metrics
        metrics = handler.get_metrics()
        assert metrics.execution_time_seconds > 0
        assert metrics.prompt_tokens == 250
        assert metrics.completion_tokens == 60
        assert metrics.total_tokens == 310
        assert metrics.tools_count == 1
        assert "check_policy_coverage" in metrics.tools_called
        assert metrics.estimated_cost_usd > 0.0

    def test_callback_tool_error_handling(self) -> None:
        handler = AgentAuditorCallbackHandler()
        handler.on_tool_start(
            serialized={"name": "failing_tool"},
            input_str="invalid params",
        )
        handler.on_tool_error(
            error=ValueError("Invalid parameter passed"),
            input={"invalid": True},
        )

        assert len(handler.tool_calls_trace) == 1
        assert "error" in handler.tool_calls_trace[0].observation
        assert "Invalid parameter" in handler.tool_calls_trace[0].observation["error"]


class TestEndToEndTraceabilityInEvaluation:
    """Tests validating that ClaimAssessment contains full observability data."""

    def test_assessment_contains_complete_traces_and_metrics(self) -> None:
        agent = ClaimEvaluatorAgent()
        claim_text = "El vehículo sufrió rotura total del parabrisas delantero por impacto de piedra."

        assessment = agent.evaluate(
            claim=claim_text,
            claim_id="CLM-AUDIT-001",
            force_deterministic=True,
        )

        # 1. DoD: Captura de pasos intermedios (Intermediate Steps)
        assert len(assessment.intermediate_steps) == 3
        step1 = assessment.intermediate_steps[0]
        step2 = assessment.intermediate_steps[1]
        step3 = assessment.intermediate_steps[2]

        # 2. DoD: Registro de qué herramientas se llamaron y parámetros exactos
        assert step1["tool"] == "check_policy_coverage"
        assert "damage_type" in step1["tool_input"]
        assert step1["observation"]["cubierto"] is True

        assert step2["tool"] == "assess_claim_risk_and_dispute"
        assert "claim_text" in step2["tool_input"]
        assert step2["observation"]["requiere_peritaje"] is False

        assert step3["tool"] == "calculate_repair_estimate"
        assert "damaged_zone" in step3["tool_input"]
        assert "severity" in step3["tool_input"]
        assert "deductible" in step3["tool_input"]
        assert step3["observation"]["total_a_pagar"] > 0

        # 3. DoD: Métricas calculadas (tiempo en segundos y tokens consumidos)
        metrics = assessment.metrics
        assert metrics.execution_time_seconds > 0.0
        assert metrics.prompt_tokens > 0
        assert metrics.completion_tokens > 0
        assert metrics.total_tokens == metrics.prompt_tokens + metrics.completion_tokens
        assert metrics.estimated_cost_usd >= 0.0
        assert metrics.tools_count == 3
        assert "check_policy_coverage" in metrics.tools_called
        assert "assess_claim_risk_and_dispute" in metrics.tools_called
        assert "calculate_repair_estimate" in metrics.tools_called

        # Alias property check
        assert assessment.execution_metrics.total_tokens == metrics.total_tokens

    def test_denied_claim_has_single_tool_trace_and_metrics(self) -> None:
        agent = ClaimEvaluatorAgent()
        claim_text = "Desgaste natural de pastillas de freno por kilometraje elevado."

        assessment = agent.evaluate(
            claim=claim_text,
            claim_id="CLM-AUDIT-002",
            force_deterministic=True,
        )

        assert assessment.status == CoverageStatus.DENIED
        assert len(assessment.intermediate_steps) == 1
        assert assessment.intermediate_steps[0]["tool"] == "check_policy_coverage"
        assert assessment.metrics.tools_count == 1
        assert assessment.metrics.execution_time_seconds > 0.0
        assert assessment.metrics.total_tokens > 0


class TestAuditReportFormatters:
    """Tests for Markdown audit logger, Mermaid flowchart, and JSON export."""

    @pytest.fixture
    def sample_assessment(self) -> ClaimAssessment:
        breakdown = CostBreakdown(materials=240.0, labor=110.0, deductible=0.0)
        metrics = ExecutionMetrics(
            execution_time_seconds=0.045,
            prompt_tokens=450,
            completion_tokens=120,
            total_tokens=570,
            estimated_cost_usd=0.000139,
            model_name="gpt-4o-mini",
            tools_called=["check_policy_coverage", "calculate_repair_estimate"],
            tools_count=2,
        )
        return ClaimAssessment(
            claim_id="CLM-REPORT-001",
            status=CoverageStatus.APPROVED,
            is_covered=True,
            coverage_summary="Rotura de lunas cubierta sin franquicia.",
            cost_breakdown=breakdown,
            reasoning="Parabrisas reparado según baremos Allianz.",
            recommendation="Emitir pago al taller concertado.",
            intermediate_steps=[
                {
                    "step_number": 1,
                    "tool": "check_policy_coverage",
                    "tool_input": {"damage_type": "parabrisas", "policy_type": "Auto"},
                    "observation": {"cubierto": True, "franquicia_estandar": 0.0},
                    "thought": "Verificando cobertura de rotura de lunas...",
                },
                {
                    "step_number": 2,
                    "tool": "calculate_repair_estimate",
                    "tool_input": {"damaged_zone": "luna delantera", "severity": "Moderado", "deductible": 0.0},
                    "observation": {"total_a_pagar": 350.0},
                    "thought": "Calculando baremo oficial de sustitución de luna...",
                },
            ],
            metrics=metrics,
        )

    def test_format_audit_log_markdown(self, sample_assessment: ClaimAssessment) -> None:
        md = format_audit_log_markdown(sample_assessment)

        assert "### 📋 Registro de Auditoría y Trazabilidad" in md
        assert "CLM-REPORT-001" in md
        assert "Tiempo Total de Ejecución" in md
        assert "0.045 s" in md
        assert "Tokens Totales" in md
        assert "`570` tokens" in md
        assert "check_policy_coverage" in md
        assert "calculate_repair_estimate" in md
        assert "Verificando cobertura" in md
        assert "Dictamen Final" in md
        assert "Aprobado" in md


    def test_format_reasoning_flow_mermaid(self, sample_assessment: ClaimAssessment) -> None:
        mermaid = format_reasoning_flow_mermaid(sample_assessment)

        assert "```mermaid" in mermaid
        assert "flowchart TD" in mermaid
        assert "CLM-REPORT-001" in mermaid
        assert "check_policy_coverage" in mermaid
        assert "calculate_repair_estimate" in mermaid
        assert "Human-in-the-loop" in mermaid

    def test_export_audit_trail_dict(self, sample_assessment: ClaimAssessment) -> None:
        trail = export_audit_trail_dict(sample_assessment)

        assert trail["claim_id"] == "CLM-REPORT-001"
        assert trail["status"] == "Aprobado"
        assert trail["is_covered"] is True
        assert trail["net_payout"] == 350.0
        assert trail["metrics"]["total_tokens"] == 570
        assert len(trail["intermediate_steps"]) == 2
        assert trail["cost_breakdown"]["gross_total"] == 350.0

        # Validate JSON serialization roundtrip
        json_dump = json.dumps(trail)
        assert json_dump is not None
        assert "CLM-REPORT-001" in json_dump
