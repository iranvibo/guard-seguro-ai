"""Agent module: LLM orchestration, ReAct tool-calling agent, and tracing for Allianz Spain."""

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

__all__ = [
    "ClaimEvaluatorAgent",
    "build_claim_agent",
    "evaluate_claim",
    "evaluate_anonymized_claim",
    "DEFAULT_AGENT_TOOLS",
    "SYSTEM_PROMPT",
    "HUMAN_PROMPT_TEMPLATE",
    "get_claim_prompt_template",
    "parse_claim_assessment_output",
    "format_intermediate_steps",
    "extract_json_from_text",
]
