"""Unit and integration tests for US-06: ReAct Agent with Tool-Calling capabilities.

Tests prompt construction, tool integration, intermediate steps capture,
deterministic execution fallbacks, mock LLM execution, and ClaimAssessment validation.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from langchain.agents import AgentExecutor
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from src.agent.claim_agent import (
    DEFAULT_AGENT_TOOLS,
    ClaimEvaluatorAgent,
    build_claim_agent,
    evaluate_anonymized_claim,
    evaluate_claim,
)
from src.agent.parser import (
    extract_json_from_text,
    format_intermediate_steps,
    parse_claim_assessment_output,
)
from src.agent.prompts import (
    HUMAN_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
    get_claim_prompt_template,
)
from src.core.config import Settings
from src.core.models import (
    AnonymizedClaim,
    ClaimAssessment,
    ClaimInput,
    CostBreakdown,
    CoverageStatus,
)
from src.privacy.masker import anonymize_claim, mask_pii


class TestAgentPrompts:
    """Validate prompt templates and system prompt contents."""

    def test_system_prompt_role_and_instructions(self) -> None:
        """Verify the system prompt sets the explicit GuardSeguro Seguros role and instructions."""
        assert "Asistente de evaluación de siniestros para GuardSeguro Seguros" in SYSTEM_PROMPT
        assert "check_policy_coverage" in SYSTEM_PROMPT
        assert "calculate_repair_estimate" in SYSTEM_PROMPT
        assert "status" in SYSTEM_PROMPT
        assert "Aprobado" in SYSTEM_PROMPT
        assert "Denegado" in SYSTEM_PROMPT
        assert "Requiere Peritaje" in SYSTEM_PROMPT

    def test_system_prompt_zero_redundancy_rules(self) -> None:
        """Verify the system prompt enforces single tool execution and early stop."""
        assert "ZERO REDUNDANCY" in SYSTEM_PROMPT or "Cero llamadas duplicadas" in SYSTEM_PROMPT
        assert "COMO MÁXIMO UNA VEZ" in SYSTEM_PROMPT
        assert "Early Stop" in SYSTEM_PROMPT or "Parada Inmediata" in SYSTEM_PROMPT

    def test_prompt_template_structure(self) -> None:
        """Verify ChatPromptTemplate input variables and structure."""
        prompt_template = get_claim_prompt_template()
        input_vars = prompt_template.input_variables

        assert "claim_id" in input_vars
        assert "policy_type" in input_vars
        assert "claim_text" in input_vars
        assert "agent_scratchpad" in input_vars

    def test_human_prompt_formatting(self) -> None:
        """Verify human prompt formats correctly with placeholders."""
        formatted = HUMAN_PROMPT_TEMPLATE.format(
            claim_id="CLM-12345",
            policy_type="Auto",
            claim_text="Impacto de granizo en techo y parabrisas.",
        )
        assert "CLM-12345" in formatted
        assert "Auto" in formatted
        assert "Impacto de granizo en techo y parabrisas." in formatted


class TestOutputParser:
    """Validate JSON extraction, intermediate step formatting, and ClaimAssessment parsing."""

    def test_extract_json_direct_string(self) -> None:
        raw = '{"status": "Aprobado", "is_covered": true, "net_payout": 350.0}'
        extracted = extract_json_from_text(raw)
        assert extracted is not None
        assert extracted["status"] == "Aprobado"
        assert extracted["is_covered"] is True
        assert extracted["net_payout"] == 350.0

    def test_extract_json_from_markdown_code_block(self) -> None:
        raw = (
            "Aquí está la resolución del siniestro:\n"
            "```json\n"
            "{\n"
            '  "status": "Denegado",\n'
            '  "is_covered": false,\n'
            '  "reasoning": "Exclusión por alcoholemia positiva."\n'
            "}\n"
            "```\n"
            "Espero que sirva."
        )
        extracted = extract_json_from_text(raw)
        assert extracted is not None
        assert extracted["status"] == "Denegado"
        assert extracted["is_covered"] is False
        assert "alcoholemia" in extracted["reasoning"]

    def test_extract_json_fallback_substring(self) -> None:
        raw = 'Texto previo {"status": "Requiere Peritaje", "is_covered": false} Texto posterior'
        extracted = extract_json_from_text(raw)
        assert extracted is not None
        assert extracted["status"] == "Requiere Peritaje"

    def test_extract_json_invalid(self) -> None:
        assert extract_json_from_text("") is None
        assert extract_json_from_text("Texto sin ningun json valido") is None

    def test_format_intermediate_steps(self) -> None:
        mock_action = MagicMock()
        mock_action.tool = "check_policy_coverage"
        mock_action.tool_input = {"damage_type": "rotura de luna"}
        mock_action.log = "Checking coverage..."

        steps = [(mock_action, '{"cubierto": true, "franquicia_estandar": 0.0}')]
        formatted = format_intermediate_steps(steps)

        assert len(formatted) == 1
        assert formatted[0]["step_number"] == 1
        assert formatted[0]["tool"] == "check_policy_coverage"
        assert formatted[0]["tool_input"]["damage_type"] == "rotura de luna"
        assert formatted[0]["observation"]["cubierto"] is True

    def test_parse_claim_assessment_approved(self) -> None:
        payload = {
            "status": "Aprobado",
            "is_covered": True,
            "coverage_summary": "Rotura de lunas cubierta sin franquicia.",
            "cost_breakdown": {
                "materials": 240.0,
                "labor": 110.0,
                "gross_total": 350.0,
                "deductible": 0.0,
                "net_total": 350.0,
            },
            "deductible": 0.0,
            "net_payout": 350.0,
            "reasoning": "Parabrisas agrietado reparado con baremo oficial.",
            "recommendation": "Proceder con la orden de taller.",
        }

        assessment = parse_claim_assessment_output(
            raw_output=json.dumps(payload),
            claim_id="CLM-001",
        )

        assert assessment.claim_id == "CLM-001"
        assert assessment.status == CoverageStatus.APPROVED
        assert assessment.is_covered is True
        assert assessment.cost_breakdown is not None
        assert assessment.cost_breakdown.gross_total == 350.0
        assert assessment.net_payout == 350.0
        assert assessment.deductible == 0.0

    def test_parse_claim_assessment_denied(self) -> None:
        payload = {
            "status": "Denegado",
            "is_covered": False,
            "coverage_summary": "Siniestro excluido por desgaste natural de neumáticos.",
            "deductible": 0.0,
            "net_payout": 0.0,
            "reasoning": "El desgaste paulatino no constituye un accidente.",
            "recommendation": "Enviar carta de denegación.",
        }

        assessment = parse_claim_assessment_output(
            raw_output=json.dumps(payload),
            claim_id="CLM-002",
        )

        assert assessment.claim_id == "CLM-002"
        assert assessment.status == CoverageStatus.DENIED
        assert assessment.is_covered is False
        assert assessment.net_payout == 0.0

    def test_parse_claim_assessment_malformed_fallback(self) -> None:
        assessment = parse_claim_assessment_output(
            raw_output="Salida completamente no estructurada del LLM",
            claim_id="CLM-003",
        )

        assert assessment.claim_id == "CLM-003"
        assert assessment.status == CoverageStatus.REQUIRES_EXPERT
        assert assessment.is_covered is False
        assert assessment.net_payout == 0.0


class TestBuildClaimAgent:
    """Validate agent executor construction and tool bindings."""

    def test_build_claim_agent_with_custom_settings(self) -> None:
        custom_settings = Settings(
            openai_api_key="sk-test-key-1234567890",
            openai_model_name="gpt-4o-mini",
            openai_temperature=0.0,
        )
        executor = build_claim_agent(settings=custom_settings)

        assert executor is not None
        assert len(executor.tools) == 3
        tool_names = [t.name for t in executor.tools]
        assert "check_policy_coverage" in tool_names
        assert "assess_claim_risk_and_dispute" in tool_names
        assert "calculate_repair_estimate" in tool_names
        assert executor.return_intermediate_steps is True


class TestClaimEvaluatorAgentDeterministic:
    """Validate deterministic evaluation pipeline for core insurance scenarios."""

    @pytest.fixture
    def agent(self) -> ClaimEvaluatorAgent:
        return ClaimEvaluatorAgent()

    def test_evaluate_windshield_claim_approved(self, agent: ClaimEvaluatorAgent) -> None:
        """Scenario 1: Windshield broken by stone -> Approved, 0 deductible."""
        claim_text = "El asegurado [PERSONA_1] comunica rotura de parabrisas delantero por impacto de gravilla en carretera."
        assessment = agent.evaluate(claim=claim_text, claim_id="CLM-AUTO-01", force_deterministic=True)

        assert assessment.claim_id == "CLM-AUTO-01"
        assert assessment.status == CoverageStatus.APPROVED
        assert assessment.is_covered is True
        assert assessment.deductible == 0.0
        assert assessment.net_payout > 0
        assert assessment.cost_breakdown is not None
        assert len(assessment.intermediate_steps) >= 3
        assert assessment.intermediate_steps[0]["tool"] == "check_policy_coverage"
        assert assessment.intermediate_steps[1]["tool"] == "assess_claim_risk_and_dispute"
        assert assessment.intermediate_steps[2]["tool"] == "calculate_repair_estimate"

    def test_evaluate_dispute_and_contradictory_claim_requires_expert(self, agent: ClaimEvaluatorAgent) -> None:
        """Scenario: Collision with contradictory versions, complaints and structural damage -> Requires expert appraisal."""
        claim_text = (
            "Colisión múltiple con otros dos vehículos de terceros. Existen versiones contradictorias "
            "sobre la prioridad de paso, posible exceso de velocidad y daños estructurales severos en el chasis y motor. "
            "Los terceros implicados han presentado denuncia y no hay atestado policial concluyente."
        )
        assessment = agent.evaluate(claim=claim_text, claim_id="CLM-DISPUTE-01", force_deterministic=True)

        assert assessment.status == CoverageStatus.REQUIRES_EXPERT
        assert assessment.is_covered is True
        assert "Requiere Peritaje" in assessment.status.value or assessment.status == CoverageStatus.REQUIRES_EXPERT
        assert any("contradictorias" in r.lower() or "riesgo" in r.lower() or "peritaje" in r.lower() for r in [assessment.reasoning, assessment.recommendation])


    def test_evaluate_hail_damage_claim_approved(self, agent: ClaimEvaluatorAgent) -> None:
        """Scenario 2: Atmospheric phenomena (severe hail) -> Approved."""
        claim_text = "Fuerte granizo y pedrisco que causó abolladuras graves en capó y techo del vehículo."
        assessment = agent.evaluate(claim=claim_text, claim_id="CLM-AUTO-02", force_deterministic=True)

        assert assessment.status == CoverageStatus.APPROVED
        assert assessment.is_covered is True
        assert "Granizo" in assessment.coverage_summary or "atmosf" in assessment.coverage_summary.lower()
        assert assessment.net_payout > 0

    def test_evaluate_collision_with_deductible(self, agent: ClaimEvaluatorAgent) -> None:
        """Scenario 3: Collision with own damage -> 150 EUR standard deductible subtracted."""
        claim_text = "Colisión trasera por alcance contra otro coche en cruce semafórico. Daños moderados en parachoques."
        assessment = agent.evaluate(claim=claim_text, claim_id="CLM-AUTO-03", force_deterministic=True)

        assert assessment.status == CoverageStatus.APPROVED
        assert assessment.is_covered is True
        assert assessment.deductible == 150.0
        assert assessment.cost_breakdown is not None
        assert assessment.net_payout == assessment.cost_breakdown.gross_total - 150.0

    def test_evaluate_excluded_natural_wear_denied(self, agent: ClaimEvaluatorAgent) -> None:
        """Scenario 4: Natural wear of tires -> Excluded / Denied."""
        claim_text = "Avería por desgaste natural de los neumáticos y pastillas de freno tras 90.000 km."
        assessment = agent.evaluate(claim=claim_text, claim_id="CLM-AUTO-04", force_deterministic=True)

        assert assessment.status == CoverageStatus.DENIED
        assert assessment.is_covered is False
        assert assessment.net_payout == 0.0
        assert len(assessment.intermediate_steps) == 1
        assert assessment.intermediate_steps[0]["tool"] == "check_policy_coverage"

    def test_evaluate_excluded_alcohol_negligence_denied(self, agent: ClaimEvaluatorAgent) -> None:
        """Scenario 5: Accident with alcohol positive test -> Excluded / Denied."""
        claim_text = "Accidente de tráfico tras control con resultado positivo en consumo de alcohol y alcoholemia."
        assessment = agent.evaluate(claim=claim_text, claim_id="CLM-AUTO-05", force_deterministic=True)

        assert assessment.status == CoverageStatus.DENIED
        assert assessment.is_covered is False
        assert assessment.net_payout == 0.0
        assert "Exclusión" in assessment.reasoning or "exclu" in assessment.coverage_summary.lower()

    def test_evaluate_uncatalogued_requires_expert(self, agent: ClaimEvaluatorAgent) -> None:
        """Scenario 6: Ambiguous / uncatalogued claim -> Requires expert appraisal."""
        claim_text = "Incidente extraño no especificado con ruidos extraños en el interior del habitáculo."
        assessment = agent.evaluate(claim=claim_text, claim_id="CLM-AUTO-06", force_deterministic=True)

        assert assessment.status == CoverageStatus.REQUIRES_EXPERT
        assert assessment.is_covered is False


class TestMockLLMAgentExecution:
    """Validate full agent execution cycle when calling an LLM executor."""

    def test_agent_evaluates_claim_via_mocked_executor(self) -> None:
        """Mock executor invocation to test full flow without external OpenAI API call."""
        agent = ClaimEvaluatorAgent()

        mock_payload = {
            "status": "Aprobado",
            "is_covered": True,
            "coverage_summary": "Rotura de parabrisas cubierta al 100%.",
            "cost_breakdown": {
                "materials": 240.0,
                "labor": 110.0,
                "gross_total": 350.0,
                "deductible": 0.0,
                "net_total": 350.0,
            },
            "deductible": 0.0,
            "net_payout": 350.0,
            "reasoning": "El asegurado tiene cobertura completa de lunas.",
            "recommendation": "Aprobar pago directo a Carglass.",
        }

        mock_action_1 = MagicMock()
        mock_action_1.tool = "check_policy_coverage"
        mock_action_1.tool_input = {"damage_type": "parabrisas roto", "policy_type": "Auto"}
        mock_action_1.log = "Checking policy coverage..."

        mock_action_2 = MagicMock()
        mock_action_2.tool = "calculate_repair_estimate"
        mock_action_2.tool_input = {"damaged_zone": "luna delantera", "severity": "Moderado", "deductible": 0.0}
        mock_action_2.log = "Calculating repair estimate..."

        mock_result = {
            "output": json.dumps(mock_payload),
            "intermediate_steps": [
                (mock_action_1, '{"cubierto": true, "franquicia_estandar": 0.0}'),
                (mock_action_2, '{"materiales": 240.0, "mano_de_obra": 110.0, "total_a_pagar": 350.0}'),
            ],
        }

        with patch.object(AgentExecutor, "invoke", return_value=mock_result):
            # Enforce settings with a dummy key so it goes to LLM path
            agent.settings = Settings(openai_api_key="sk-live-valid-mock-key-123456789")
            assessment = agent.evaluate(
                claim="El parabrisas de mi vehículo se ha roto tras un impacto.",
                claim_id="CLM-TEST-LLM-01",
            )

            assert assessment.claim_id == "CLM-TEST-LLM-01"
            assert assessment.status == CoverageStatus.APPROVED
            assert assessment.is_covered is True
            assert assessment.net_payout == 350.0
            assert len(assessment.intermediate_steps) == 2
            assert assessment.intermediate_steps[0]["tool"] == "check_policy_coverage"
            assert assessment.intermediate_steps[1]["tool"] == "calculate_repair_estimate"

    def test_agent_raises_runtime_error_on_api_exception_without_fallback(self) -> None:
        """Verify that when OpenAI API throws an exception (e.g. 401 auth or 429 quota),
        the agent raises RuntimeError and does NOT fall back to deterministic evaluation."""
        agent = ClaimEvaluatorAgent()
        agent.settings = Settings(openai_api_key="sk-live-dummy-key-to-trigger-llm")

        simulated_api_error = Exception(
            "Error code: 401 - Incorrect API key provided"
        )

        with patch.object(AgentExecutor, "invoke", side_effect=simulated_api_error):
            with pytest.raises(RuntimeError) as exc_info:
                agent.evaluate(
                    claim="Rotura de parabrisas delantero por piedra.",
                    claim_id="CLM-ERR-401",
                    force_deterministic=False,
                )

            assert "Error en la llamada a la API de OpenAI" in str(exc_info.value)
            assert "401" in str(exc_info.value)

    def test_agent_raises_value_error_when_no_api_key_in_openai_mode(self) -> None:
        """Verify that when OpenAI mode is selected without an API key, a ValueError is raised."""
        agent = ClaimEvaluatorAgent()
        agent.settings = Settings(openai_api_key="")

        with pytest.raises(ValueError) as exc_info:
            agent.evaluate(
                claim="Rotura de parabrisas delantero por piedra.",
                claim_id="CLM-NO-KEY",
                force_deterministic=False,
            )

        assert "API Key de OpenAI no está configurada" in str(exc_info.value)


class TestFullPipelineIntegration:
    """Validate end-to-end integration: ClaimInput -> AnonymizedClaim -> ClaimAssessment."""

    def test_claim_input_to_anonymized_claim_to_assessment(self) -> None:
        # 1. Raw input with PII
        raw_claim = ClaimInput(
            claim_id="CLM-E2E-777",
            raw_text="El conductor llamado Carlos Ruiz con DNI 45892134K y matrícula 7823 LMN sufrió un rayón intencionado con llave en la puerta.",
            policy_type="Auto",
        )

        # 2. Anonymize PII
        anonymized = anonymize_claim(raw_claim)
        assert "Carlos Ruiz" not in anonymized.anonymized_text
        assert "45892134K" not in anonymized.anonymized_text
        assert "7823 LMN" not in anonymized.anonymized_text

        # 3. Evaluate anonymized claim with Agent
        assessment = evaluate_anonymized_claim(anonymized, force_deterministic=True)

        assert assessment.claim_id == "CLM-E2E-777"
        assert assessment.status == CoverageStatus.APPROVED
        assert assessment.is_covered is True
        assert assessment.deductible == 150.0  # Vandalism deductible
        assert assessment.cost_breakdown is not None
        assert assessment.net_payout >= 0.0

    def test_convenience_evaluate_claim_with_claim_input(self) -> None:
        claim_in = ClaimInput(
            claim_id="CLM-E2E-888",
            raw_text="Rotura de luna trasera tras impacto de piedra.",
            policy_type="Auto",
        )
        assessment = evaluate_claim(claim_in, force_deterministic=True)
        assert assessment.claim_id == "CLM-E2E-888"
        assert assessment.status == CoverageStatus.APPROVED
        assert assessment.is_covered is True
