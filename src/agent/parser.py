"""Output parser and trace formatter for the GuardSeguro AI Claim Agent.

Converts raw agent output text and LLM responses into strictly typed
ClaimAssessment Pydantic models with robust fallback mechanisms.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from src.core.models import ClaimAssessment, CostBreakdown, CoverageStatus, ExecutionMetrics

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract and decode a JSON object from text or markdown code blocks.

    Args:
        text: Raw text potentially containing JSON or ```json ... ``` fences.

    Returns:
        Parsed dictionary if valid JSON is found, None otherwise.
    """
    if not text:
        return None

    stripped = text.strip()

    # 1. Direct JSON parse attempt
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Markdown fence regex: ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fence_match:
        try:
            data = json.loads(fence_match.group(1))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. First '{' to last '}' bracket extraction
    start_idx = stripped.find("{")
    end_idx = stripped.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        potential_json = stripped[start_idx : end_idx + 1]
        try:
            data = json.loads(potential_json)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def format_intermediate_steps(intermediate_steps: Optional[List[Any]]) -> List[Dict[str, Any]]:
    """Format LangChain intermediate step tuples into audit-friendly dictionaries.

    Args:
        intermediate_steps: List of (AgentAction, observation) tuples or trace dicts.

    Returns:
        Structured list of audit dictionaries with tool name, inputs, observation, thought, and log.
    """
    if not intermediate_steps:
        return []

    formatted = []
    for idx, step in enumerate(intermediate_steps, start=1):
        try:
            if isinstance(step, (tuple, list)) and len(step) >= 2:
                action, observation = step[0], step[1]
                tool_name = getattr(action, "tool", str(action))
                tool_input = getattr(action, "tool_input", {})
                action_log = getattr(action, "log", "")

                obs_payload = observation
                if isinstance(observation, str):
                    try:
                        obs_payload = json.loads(observation)
                    except Exception:
                        obs_payload = observation

                formatted.append(
                    {
                        "step_number": idx,
                        "tool": tool_name,
                        "tool_input": tool_input,
                        "observation": obs_payload,
                        "thought": action_log.strip() if action_log else "",
                        "log": action_log,
                    }
                )
            elif isinstance(step, dict):
                entry = dict(step)
                if "step_number" not in entry:
                    entry["step_number"] = idx
                if "thought" not in entry and "log" in entry:
                    entry["thought"] = entry["log"]
                formatted.append(entry)
            else:
                formatted.append({"step_number": idx, "raw_step": str(step)})
        except Exception as exc:
            logger.warning("Error formatting intermediate step %d: %s", idx, exc)
            formatted.append({"step_number": idx, "raw_step": str(step)})

    return formatted


def parse_claim_assessment_output(
    raw_output: str,
    claim_id: str,
    intermediate_steps: Optional[List[Any]] = None,
    metrics: Optional[ExecutionMetrics] = None,
) -> ClaimAssessment:
    """Parse raw agent string output into a validated ClaimAssessment model.

    Args:
        raw_output: String output returned by the agent.
        claim_id: Unique claim identifier.
        intermediate_steps: Optional list of intermediate steps from execution.
        metrics: Optional execution metrics (latency, token usage, cost).

    Returns:
        Validated ClaimAssessment Pydantic model instance.
    """
    formatted_steps = format_intermediate_steps(intermediate_steps)
    json_data = extract_json_from_text(raw_output)
    execution_metrics = metrics or ExecutionMetrics()

    if json_data:
        try:
            # Map status to CoverageStatus enum safely
            raw_status = str(json_data.get("status", "Requiere Peritaje")).strip()
            if "aprob" in raw_status.lower():
                status = CoverageStatus.APPROVED
            elif "deneg" in raw_status.lower():
                status = CoverageStatus.DENIED
            else:
                status = CoverageStatus.REQUIRES_EXPERT

            is_covered = bool(json_data.get("is_covered", status == CoverageStatus.APPROVED))

            # Parse cost breakdown
            cost_data = json_data.get("cost_breakdown")
            cost_breakdown = None
            if isinstance(cost_data, dict) and is_covered:
                try:
                    cost_breakdown = CostBreakdown(
                        materials=float(cost_data.get("materials", 0.0)),
                        labor=float(cost_data.get("labor", 0.0)),
                        deductible=float(cost_data.get("deductible", json_data.get("deductible", 0.0))),
                    )
                except Exception as exc:
                    logger.warning("Failed to construct CostBreakdown from dict: %s", exc)

            deductible = float(json_data.get("deductible", 0.0))
            if cost_breakdown:
                deductible = cost_breakdown.deductible

            net_payout = float(json_data.get("net_payout", 0.0))
            if cost_breakdown and is_covered:
                net_payout = cost_breakdown.net_total
            elif not is_covered:
                net_payout = 0.0

            coverage_summary = str(
                json_data.get("coverage_summary", "Evaluación de cobertura procesada por el agente.")
            ).strip()

            reasoning = str(
                json_data.get("reasoning", raw_output)
            ).strip()

            recommendation = str(
                json_data.get("recommendation", "Revisión y validación por gestor humano requerida.")
            ).strip()

            return ClaimAssessment(
                claim_id=claim_id,
                status=status,
                is_covered=is_covered,
                coverage_summary=coverage_summary,
                cost_breakdown=cost_breakdown,
                deductible=deductible,
                net_payout=net_payout,
                reasoning=reasoning,
                recommendation=recommendation,
                intermediate_steps=formatted_steps,
                metrics=execution_metrics,
            )
        except Exception as exc:
            logger.error("Error building ClaimAssessment from JSON payload: %s. Using fallback.", exc)

    # Fallback when no structured JSON could be parsed
    logger.warning("Agent output could not be parsed as structured JSON for claim %s", claim_id)
    return ClaimAssessment(
        claim_id=claim_id,
        status=CoverageStatus.REQUIRES_EXPERT,
        is_covered=False,
        coverage_summary="Respuesta no estructurada del modelo. Requiere revisión pericial.",
        cost_breakdown=None,
        deductible=0.0,
        net_payout=0.0,
        reasoning=raw_output or "El agente no produjo una respuesta estructurada.",
        recommendation="Revisión obligatoria por gestor humano debido a salida no estructurada.",
        intermediate_steps=formatted_steps,
        metrics=execution_metrics,
    )
