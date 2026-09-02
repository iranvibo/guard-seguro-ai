"""Claim assessment ReAct agent using LangChain tool calling for Allianz Spain.

Coordinates policy coverage checking and repair cost calculation tools to produce
strongly typed, auditable ClaimAssessment resolutions.
"""

import json
import logging
import time
from typing import Any, List, Optional, Union

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from src.agent.observability import (
    AgentAuditorCallbackHandler,
    calculate_token_cost,
    estimate_text_tokens,
)
from src.agent.parser import parse_claim_assessment_output
from src.agent.prompts import SYSTEM_PROMPT, get_claim_prompt_template
from src.core.config import Settings, get_settings
from src.core.models import (
    AnonymizedClaim,
    ClaimAssessment,
    ClaimInput,
    CoverageStatus,
    DamageSeverity,
    ExecutionMetrics,
)
from src.tools.policy_coverage import check_policy_coverage, verify_policy_coverage
from src.tools.repair_calculator import calculate_repair_estimate, compute_repair_estimate

logger = logging.getLogger(__name__)

DEFAULT_AGENT_TOOLS: List[BaseTool] = [
    check_policy_coverage,
    calculate_repair_estimate,
]


def build_claim_agent(
    llm: Optional[BaseChatModel] = None,
    tools: Optional[List[BaseTool]] = None,
    settings: Optional[Settings] = None,
    max_iterations: int = 10,
    verbose: bool = False,
) -> AgentExecutor:
    """Build and configure a LangChain tool-calling AgentExecutor for claim evaluation.

    Args:
        llm: Optional pre-instantiated chat model (e.g., ChatOpenAI or mock).
        tools: Optional list of LangChain tools. Defaults to check_policy_coverage & calculate_repair_estimate.
        settings: Application settings for API key and model config.
        max_iterations: Maximum iterations before terminating agent execution loop.
        verbose: Whether to log agent thoughts to stdout.

    Returns:
        Configured AgentExecutor ready to evaluate claims.
    """
    if settings is None:
        settings = get_settings()

    if tools is None:
        tools = DEFAULT_AGENT_TOOLS

    if llm is None:
        if not settings.is_api_key_configured:
            logger.warning("OpenAI API key is not configured. Real LLM calls may fail.")
        llm = ChatOpenAI(
            model=settings.openai_model_name,
            temperature=settings.openai_temperature,
            api_key=settings.openai_api_key or "sk-dummy-key-for-initialization",
        )

    prompt = get_claim_prompt_template()
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        return_intermediate_steps=True,
        max_iterations=max_iterations,
        handle_parsing_errors=True,
    )


class ClaimEvaluatorAgent:
    """Orchestrator for automated claim evaluation with ReAct tool-calling, observability and governance."""

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        tools: Optional[List[BaseTool]] = None,
        settings: Optional[Settings] = None,
        max_iterations: int = 10,
        verbose: bool = False,
    ) -> None:
        """Initialize the ClaimEvaluatorAgent.

        Args:
            llm: Optional custom chat model.
            tools: Optional custom tools.
            settings: Optional custom Settings.
            max_iterations: Max reasoning iterations.
            verbose: Verbose logging flag.
        """
        self.settings = settings or get_settings()
        self.tools = tools or DEFAULT_AGENT_TOOLS
        self.llm = llm
        self.max_iterations = max_iterations
        self.verbose = verbose
        self._executor: Optional[AgentExecutor] = None

    @property
    def executor(self) -> AgentExecutor:
        """Get or lazily initialize the AgentExecutor."""
        if self._executor is None:
            self._executor = build_claim_agent(
                llm=self.llm,
                tools=self.tools,
                settings=self.settings,
                max_iterations=self.max_iterations,
                verbose=self.verbose,
            )
        return self._executor

    def evaluate_deterministic_mock(
        self,
        claim_text: str,
        claim_id: str,
        policy_type: str = "Auto",
        api_error: Optional[str] = None,
    ) -> ClaimAssessment:
        """Deterministic evaluation pipeline used for offline testing, demos, or fallback.

        Executes the exact same underlying tools (verify_policy_coverage & compute_repair_estimate)
        and constructs a fully verified ClaimAssessment with realistic intermediate steps,
        latency measurements, and token consumption metrics (US-07).

        Args:
            claim_text: Anonymized text of the claim.
            claim_id: Identifier of the claim.
            policy_type: Type of policy (Auto, Hogar).
            api_error: Optional error string if triggered as fallback from real LLM failure.

        Returns:
            Validated ClaimAssessment instance with populated metrics and traces.
        """
        logger.info("Executing deterministic claim evaluation for %s", claim_id)
        start_time = time.perf_counter()
        tools_called: List[str] = ["check_policy_coverage"]

        # 1. Step 1: Coverage Check Tool
        t0 = time.perf_counter()
        cov_res = verify_policy_coverage(damage_type=claim_text, policy_type=policy_type)
        t_cov = round(time.perf_counter() - t0, 4)

        cov_tool_output = {
            "cubierto": cov_res.is_covered,
            "condiciones": cov_res.conditions,
            "franquicia_estandar": cov_res.standard_deductible,
            "tipo_cobertura": cov_res.coverage_type,
            "is_covered": cov_res.is_covered,
        }

        intermediate_steps: List[Any] = [
            (
                type("AgentActionMock", (), {
                    "tool": "check_policy_coverage",
                    "tool_input": {"damage_type": claim_text[:80], "policy_type": policy_type},
                    "log": f"Invoking check_policy_coverage for '{claim_text[:50]}...'",
                })(),
                json.dumps(cov_tool_output, ensure_ascii=False),
            )
        ]

        # 2. Step 2: Repair Calculation (if covered)
        cost_breakdown = None
        if cov_res.is_covered:
            tools_called.append("calculate_repair_estimate")
            # Estimate severity from text
            severity = DamageSeverity.LIGHT
            lower_text = claim_text.lower()
            if any(k in lower_text for k in ["grave", "severo", "siniestro total", "destrozado", "arrancado", "fuerte impacto"]):
                severity = DamageSeverity.SEVERE
            elif any(k in lower_text for k in ["moderado", "abolladura", "grieta", "rotura", "golpe", "colision"]):
                severity = DamageSeverity.MODERATE

            t1 = time.perf_counter()
            breakdown, meta = compute_repair_estimate(
                damaged_zone=claim_text,
                severity=severity,
                deductible=cov_res.standard_deductible,
            )
            t_calc = round(time.perf_counter() - t1, 4)
            cost_breakdown = breakdown

            calc_tool_output = {
                "materiales": breakdown.materials,
                "mano_de_obra": breakdown.labor,
                "coste_bruto": breakdown.gross_total,
                "franquicia": breakdown.deductible,
                "total_a_pagar": breakdown.net_total,
                "zona_afectada": meta["zone_name"],
                "gravedad": meta["severity"],
                "detalle": meta["description"],
            }

            intermediate_steps.append(
                (
                    type("AgentActionMock", (), {
                        "tool": "calculate_repair_estimate",
                        "tool_input": {
                            "damaged_zone": meta["zone_name"],
                            "severity": meta["severity"],
                            "deductible": cov_res.standard_deductible,
                        },
                        "log": f"Invoking calculate_repair_estimate for zone '{meta['zone_name']}' with severity '{meta['severity']}'.",
                    })(),
                    json.dumps(calc_tool_output, ensure_ascii=False),
                )
            )

            status = CoverageStatus.APPROVED
            summary = f"Siniestro cubierto bajo garantía de '{cov_res.coverage_type}'."
            reasoning = (
                f"El incidente reportado corresponde a la cobertura '{cov_res.coverage_type}'. "
                f"Condiciones: {cov_res.conditions}. "
                f"Se ha calculado el coste técnico de reparación para {meta['zone_name']} (Gravedad: {meta['severity']}): "
                f"Materiales ({breakdown.materials:.2f} €) + Mano de Obra ({breakdown.labor:.2f} €) = {breakdown.gross_total:.2f} €. "
                f"Aplicando franquicia de {breakdown.deductible:.2f} €, el total indemnizable es {breakdown.net_total:.2f} €."
            )
            recommendation = "Proceder a la emisión de la orden de reparación o indemnización tras visto bueno del gestor."
        elif "requiere peritaje" in cov_res.coverage_type.lower() or "no catalogado" in cov_res.coverage_type.lower():
            status = CoverageStatus.REQUIRES_EXPERT
            summary = "Siniestro de tipología compleja o no tipificada. Requiere valoración pericial."
            reasoning = (
                f"El siniestro no ha podido ser clasificado automáticamente de forma unívoca ({cov_res.coverage_type}). "
                f"Condición: {cov_res.conditions}. Por seguridad y gobernanza, se deriva a peritaje técnico."
            )
            recommendation = "Asignar a perito presencial o gabinete pericial para inspección física y valoración."
        else:
            status = CoverageStatus.DENIED
            summary = f"Siniestro no cubierto por la póliza ({cov_res.coverage_type})."
            reasoning = (
                f"El siniestro queda excluido de la póliza de acuerdo con el condicionado general: {cov_res.conditions}. "
                f"Motivo: {cov_res.coverage_type}."
            )
            recommendation = "Notificar al asegurado la resolución motivada de denegación de cobertura con derecho a alegación."

        synthetic_payload = {
            "status": status.value,
            "is_covered": cov_res.is_covered,
            "coverage_summary": summary,
            "cost_breakdown": (
                {
                    "materials": cost_breakdown.materials,
                    "labor": cost_breakdown.labor,
                    "gross_total": cost_breakdown.gross_total,
                    "deductible": cost_breakdown.deductible,
                    "net_total": cost_breakdown.net_total,
                }
                if cost_breakdown
                else None
            ),
            "deductible": cov_res.standard_deductible if cost_breakdown else 0.0,
            "net_payout": cost_breakdown.net_total if cost_breakdown else 0.0,
            "reasoning": reasoning,
            "recommendation": recommendation,
        }

        # Calculate metrics (US-07)
        raw_json_str = json.dumps(synthetic_payload, ensure_ascii=False)
        total_duration = round(max(0.001, time.perf_counter() - start_time), 4)

        # Estimate realistic token counts
        prompt_text = f"{SYSTEM_PROMPT}\nclaim_id: {claim_id}\npolicy_type: {policy_type}\nclaim_text: {claim_text}"
        prompt_tokens = estimate_text_tokens(prompt_text)
        completion_tokens = estimate_text_tokens(raw_json_str)
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = calculate_token_cost(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_name=self.settings.openai_model_name,
        )

        metrics = ExecutionMetrics(
            execution_time_seconds=total_duration,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost_usd,
            model_name=self.settings.openai_model_name,
            tools_called=tools_called,
            tools_count=len(tools_called),
        )

        parsed = parse_claim_assessment_output(
            raw_output=raw_json_str,
            claim_id=claim_id,
            intermediate_steps=intermediate_steps,
            metrics=metrics,
        )
        if api_error:
            parsed.api_error = api_error
        return parsed

    def evaluate(
        self,
        claim: Union[AnonymizedClaim, ClaimInput, str],
        claim_id: Optional[str] = None,
        policy_type: str = "Auto",
        force_deterministic: bool = False,
    ) -> ClaimAssessment:
        """Evaluate a claim end-to-end through the ReAct agent with observability tracking.

        Args:
            claim: AnonymizedClaim model, ClaimInput model, or raw string.
            claim_id: Optional claim id if claim is passed as string.
            policy_type: Type of policy (Auto, Hogar).
            force_deterministic: If True, bypass LLM API and use deterministic engine.

        Returns:
            Validated ClaimAssessment instance.
        """
        # 1. Normalize input
        if isinstance(claim, AnonymizedClaim):
            target_claim_id = claim.claim_id
            target_text = claim.anonymized_text
        elif isinstance(claim, ClaimInput):
            target_claim_id = claim.claim_id
            target_text = claim.raw_text
            policy_type = claim.policy_type
        else:
            target_claim_id = claim_id or "CLM-UNKNOWN"
            target_text = str(claim)

        # 2. Check if we should use deterministic mock or real LLM
        if force_deterministic or not self.settings.is_api_key_configured:
            if not force_deterministic:
                logger.info(
                    "OpenAI API key not provided. Falling back to deterministic tool evaluation for claim %s",
                    target_claim_id,
                )
            return self.evaluate_deterministic_mock(
                claim_text=target_text,
                claim_id=target_claim_id,
                policy_type=policy_type,
            )

        # 3. Real LLM Tool-Calling Agent Execution with Auditing Callback (US-07)
        auditor = AgentAuditorCallbackHandler(model_name=self.settings.openai_model_name)
        start_time = time.perf_counter()

        try:
            logger.info("Invoking LLM ReAct agent for claim %s", target_claim_id)
            inputs = {
                "claim_id": target_claim_id,
                "policy_type": policy_type,
                "claim_text": target_text,
            }
            result = self.executor.invoke(inputs, config={"callbacks": [auditor]})

            raw_output = result.get("output", "")
            intermediate_steps = result.get("intermediate_steps", [])

            metrics = auditor.get_metrics()
            # If start_time / latency was captured from external timer
            if metrics.execution_time_seconds == 0.0:
                metrics.execution_time_seconds = round(max(0.001, time.perf_counter() - start_time), 3)

            # Ensure tool count and names match if captured by callback
            if not metrics.tools_called and intermediate_steps:
                metrics.tools_called = [
                    getattr(step[0], "tool", "unknown_tool")
                    for step in intermediate_steps
                    if isinstance(step, (tuple, list)) and len(step) >= 1
                ]
                metrics.tools_count = len(metrics.tools_called)

            return parse_claim_assessment_output(
                raw_output=raw_output,
                claim_id=target_claim_id,
                intermediate_steps=intermediate_steps,
                metrics=metrics,
            )
        except Exception as exc:
            error_msg = str(exc)
            logger.error(
                "Error during LLM agent execution for %s: %s. Falling back to deterministic engine.",
                target_claim_id,
                error_msg,
            )
            return self.evaluate_deterministic_mock(
                claim_text=target_text,
                claim_id=target_claim_id,
                policy_type=policy_type,
                api_error=error_msg,
            )


def evaluate_claim(
    claim: Union[AnonymizedClaim, ClaimInput, str],
    claim_id: Optional[str] = None,
    policy_type: str = "Auto",
    llm: Optional[BaseChatModel] = None,
    settings: Optional[Settings] = None,
    force_deterministic: bool = False,
) -> ClaimAssessment:
    """Convenience function to evaluate a claim using ClaimEvaluatorAgent.

    Args:
        claim: AnonymizedClaim, ClaimInput, or string claim text.
        claim_id: Identifier of the claim.
        policy_type: Type of policy (Auto, Hogar).
        llm: Optional chat model instance.
        settings: Optional Settings instance.
        force_deterministic: Flag to enforce offline deterministic execution.

    Returns:
        Structured ClaimAssessment.
    """
    agent = ClaimEvaluatorAgent(llm=llm, settings=settings)
    return agent.evaluate(
        claim=claim,
        claim_id=claim_id,
        policy_type=policy_type,
        force_deterministic=force_deterministic,
    )


def evaluate_anonymized_claim(
    anonymized_claim: AnonymizedClaim,
    llm: Optional[BaseChatModel] = None,
    settings: Optional[Settings] = None,
    force_deterministic: bool = False,
) -> ClaimAssessment:
    """Evaluate an AnonymizedClaim model instance.

    Args:
        anonymized_claim: AnonymizedClaim model.
        llm: Optional chat model.
        settings: Optional Settings.
        force_deterministic: Flag to enforce offline deterministic execution.

    Returns:
        Structured ClaimAssessment.
    """
    return evaluate_claim(
        claim=anonymized_claim,
        llm=llm,
        settings=settings,
        force_deterministic=force_deterministic,
    )


def evaluate_claim_with_compliance(
    claim: Union[AnonymizedClaim, ClaimInput, str],
    claim_id: Optional[str] = None,
    policy_type: str = "Auto",
    llm: Optional[BaseChatModel] = None,
    settings: Optional[Settings] = None,
    force_deterministic: bool = False,
) -> tuple[ClaimAssessment, Any]:
    """Evaluate a claim and immediately generate its EU AI Act Compliance Report (US-08).

    Args:
        claim: AnonymizedClaim, ClaimInput, or string claim text.
        claim_id: Identifier of the claim.
        policy_type: Type of policy (Auto, Hogar).
        llm: Optional chat model instance.
        settings: Optional Settings instance.
        force_deterministic: Flag to enforce offline deterministic execution.

    Returns:
        Tuple of (ClaimAssessment, EUAIActComplianceReport).
    """
    from src.compliance.auditor import generate_compliance_report

    assessment = evaluate_claim(
        claim=claim,
        claim_id=claim_id,
        policy_type=policy_type,
        llm=llm,
        settings=settings,
        force_deterministic=force_deterministic,
    )

    anonymized_claim = claim if isinstance(claim, AnonymizedClaim) else None
    claim_input = claim if isinstance(claim, ClaimInput) else None

    compliance_report = generate_compliance_report(
        assessment=assessment,
        anonymized_claim=anonymized_claim,
        claim_input=claim_input,
    )

    return assessment, compliance_report


