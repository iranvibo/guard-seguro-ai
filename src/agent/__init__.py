"""Agent module: LLM orchestration, ReAct tool-calling agent, and tracing for Allianz Spain."""

from src.agent.claim_agent import (
    DEFAULT_AGENT_TOOLS,
    ClaimEvaluatorAgent,
    build_claim_agent,
    evaluate_anonymized_claim,
    evaluate_claim,
)
from src.agent.observability import (
    AgentAuditorCallbackHandler,
    calculate_token_cost,
    estimate_text_tokens,
    export_audit_trail_dict,
    format_audit_log_markdown,
    format_reasoning_flow_mermaid,
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
    "AgentAuditorCallbackHandler",
    "estimate_text_tokens",
    "calculate_token_cost",
    "format_audit_log_markdown",
    "format_reasoning_flow_mermaid",
    "export_audit_trail_dict",
]

