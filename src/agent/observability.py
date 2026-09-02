"""Observability, traceability, and audit logging module for GuardSeguro AI (US-07).

Provides callback handlers for LangChain agent executions, metric tracking
(latency, token consumption, estimated monetary cost), and auditing visualizers
(Markdown summary, Mermaid flowchart, JSON export).
"""

import json
import logging
import math
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Union

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from src.core.models import ClaimAssessment, ExecutionMetrics, ToolCallTrace

logger = logging.getLogger(__name__)

# Standard pricing catalog per 1,000,000 tokens (USD)
MODEL_PRICING_CATALOG: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini": {
        "prompt_price_per_1m": 0.15,
        "completion_price_per_1m": 0.60,
    },
    "gpt-4o": {
        "prompt_price_per_1m": 2.50,
        "completion_price_per_1m": 10.00,
    },
    "gpt-3.5-turbo": {
        "prompt_price_per_1m": 0.50,
        "completion_price_per_1m": 1.50,
    },
}


def estimate_text_tokens(text: str) -> int:
    """Estimate token count for a given text using average token-to-character ratio.

    In Spanish/English mixed technical domains, 1 token approximates ~3.8 characters.

    Args:
        text: Input string or serialized object.

    Returns:
        Estimated integer number of tokens (minimum 1 for non-empty text).
    """
    if not text:
        return 0
    clean_text = str(text).strip()
    if not clean_text:
        return 0
    # Average 3.8 chars per token heuristic
    return max(1, math.ceil(len(clean_text) / 3.8))


def calculate_token_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model_name: str = "gpt-4o-mini",
) -> float:
    """Calculate the estimated monetary cost in USD for the given token consumption.

    Args:
        prompt_tokens: Number of prompt/input tokens.
        completion_tokens: Number of generated/completion tokens.
        model_name: Name of the LLM model.

    Returns:
        Estimated cost in USD rounded to 6 decimal places.
    """
    # Lookup model pricing or fallback to gpt-4o-mini rates
    pricing = MODEL_PRICING_CATALOG.get(
        model_name.lower(),
        MODEL_PRICING_CATALOG["gpt-4o-mini"],
    )

    prompt_cost = (prompt_tokens / 1_000_000.0) * pricing["prompt_price_per_1m"]
    completion_cost = (completion_tokens / 1_000_000.0) * pricing["completion_price_per_1m"]

    return round(prompt_cost + completion_cost, 6)


class AgentAuditorCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that records audit traces and tracks execution metrics."""

    def __init__(self, model_name: str = "gpt-4o-mini") -> None:
        """Initialize the auditor callback handler."""
        super().__init__()
        self.model_name = model_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0

        self.tool_calls_trace: List[ToolCallTrace] = []
        self._current_tool_start_times: Dict[str, float] = {}
        self._latest_agent_thought: str = ""
        self._tools_invoked: List[str] = []

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Record overall agent execution start time."""
        if self.start_time is None:
            self.start_time = time.perf_counter()

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Record overall agent execution end time."""
        self.end_time = time.perf_counter()

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Track prompt tokens when LLM starts."""
        for prompt in prompts:
            # If no live token counters available yet, pre-estimate
            self.prompt_tokens += estimate_text_tokens(prompt)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Extract exact token usage from LLM response when provided by the provider."""
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            p_tok = usage.get("prompt_tokens")
            c_tok = usage.get("completion_tokens")
            t_tok = usage.get("total_tokens")

            if p_tok is not None:
                self.prompt_tokens = p_tok
            if c_tok is not None:
                self.completion_tokens = c_tok
            if t_tok is not None:
                self.total_tokens = t_tok
            else:
                self.total_tokens = self.prompt_tokens + self.completion_tokens
        else:
            # Fallback estimation from generated generations text
            for gen_list in response.generations:
                for gen in gen_list:
                    self.completion_tokens += estimate_text_tokens(gen.text)
            self.total_tokens = self.prompt_tokens + self.completion_tokens

    def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        """Capture the agent's thought/reasoning log before calling a tool."""
        self._latest_agent_thought = getattr(action, "log", "")

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Record tool start timestamp and tool invocation name."""
        tool_name = serialized.get("name", "unknown_tool")
        self._tools_invoked.append(tool_name)
        self._current_tool_start_times[tool_name] = time.perf_counter()

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Record tool observation output and elapsed step duration."""
        tool_name = self._tools_invoked[-1] if self._tools_invoked else "unknown_tool"
        start_t = self._current_tool_start_times.pop(tool_name, time.perf_counter())
        step_duration = round(time.perf_counter() - start_t, 4)

        # Parse output payload if JSON string
        obs_payload: Any = output
        if isinstance(output, str):
            try:
                obs_payload = json.loads(output)
            except Exception:
                obs_payload = output

        # Extract tool input if available in kwargs
        tool_input = kwargs.get("input", {})
        if not tool_input and "inputs" in kwargs:
            tool_input = kwargs["inputs"]

        step_idx = len(self.tool_calls_trace) + 1
        trace = ToolCallTrace(
            step_number=step_idx,
            tool=tool_name,
            tool_input=tool_input if isinstance(tool_input, dict) else {"input": str(tool_input)},
            observation=obs_payload,
            thought=self._latest_agent_thought,
            execution_time_seconds=step_duration,
            timestamp=datetime.now(),
        )
        self.tool_calls_trace.append(trace)
        self._latest_agent_thought = ""

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """Record tool errors in audit trail."""
        tool_name = self._tools_invoked[-1] if self._tools_invoked else "unknown_tool"
        step_idx = len(self.tool_calls_trace) + 1
        trace = ToolCallTrace(
            step_number=step_idx,
            tool=tool_name,
            tool_input=kwargs.get("input", {}),
            observation={"error": str(error)},
            thought=f"Error during tool execution: {error}",
            execution_time_seconds=0.0,
            timestamp=datetime.now(),
        )
        self.tool_calls_trace.append(trace)

    def get_metrics(self) -> ExecutionMetrics:
        """Compute and return the structured ExecutionMetrics summary."""
        duration = 0.0
        if self.start_time is not None:
            end_t = self.end_time if self.end_time is not None else time.perf_counter()
            duration = round(max(0.0, end_t - self.start_time), 3)

        cost_usd = calculate_token_cost(
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            model_name=self.model_name,
        )

        return ExecutionMetrics(
            execution_time_seconds=duration,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.total_tokens or (self.prompt_tokens + self.completion_tokens),
            estimated_cost_usd=cost_usd,
            model_name=self.model_name,
            tools_called=[t.tool for t in self.tool_calls_trace] or self._tools_invoked,
            tools_count=len(self.tool_calls_trace) or len(self._tools_invoked),
        )

    def get_traces_as_dict(self) -> List[Dict[str, Any]]:
        """Return formatted list of tool traces as audit dictionaries."""
        return [
            {
                "step_number": t.step_number,
                "tool": t.tool,
                "tool_input": t.tool_input,
                "observation": t.observation,
                "thought": t.thought,
                "execution_time_seconds": t.execution_time_seconds,
                "timestamp": t.timestamp.isoformat(),
            }
            for t in self.tool_calls_trace
        ]


def format_audit_log_markdown(assessment: ClaimAssessment) -> str:
    """Generate a clean, structured Markdown audit report for a ClaimAssessment.

    Args:
        assessment: ClaimAssessment model instance containing intermediate steps and metrics.

    Returns:
        Formatted Markdown text ready for Streamlit rendering, compliance review, or logs.
    """
    metrics = assessment.metrics
    lines: List[str] = [
        f"### 📋 Registro de Auditoría y Trazabilidad — Reclamación `{assessment.claim_id}`",
        "",
        "#### ⏱️ Métricas de Ejecución y Consumo",
        "| Métrica | Valor |",
        "|---|---|",
        f"| **Tiempo Total de Ejecución** | `{metrics.execution_time_seconds:.3f} s` |",
        f"| **Modelo Utilizado** | `{metrics.model_name}` |",
        f"| **Tokens de Entrada (Prompt)** | `{metrics.prompt_tokens}` tokens |",
        f"| **Tokens de Salida (Completion)** | `{metrics.completion_tokens}` tokens |",
        f"| **Tokens Totales** | `{metrics.total_tokens}` tokens |",
        f"| **Coste Estimado** | `${metrics.estimated_cost_usd:.6f} USD` |",
        f"| **Herramientas Invocadas** | `{metrics.tools_count}` llamadas ({', '.join(metrics.tools_called) or 'Ninguna'}) |",
        "",
        "#### 🔍 Secuencia de Razonamiento y Pasos Intermedios (*Thought / Action / Observation*)",
    ]

    if not assessment.intermediate_steps:
        lines.append("_No se registraron pasos intermedios (ejecución directa o dictamen sin herramientas)._")
    else:
        for step in assessment.intermediate_steps:
            step_num = step.get("step_number", 1)
            tool_name = step.get("tool", "Herramienta")
            tool_input = step.get("tool_input", {})
            obs = step.get("observation", {})
            thought = step.get("thought") or step.get("log") or "Razonamiento del agente para invocar herramienta."

            lines.append(f"##### **Paso {step_num}: Invocación de `{tool_name}`**")
            if thought:
                lines.append(f"- **🧠 Razonamiento (Thought):** {thought.strip()}")
            lines.append(f"- **🛠️ Acción y Parámetros (Action Input):**")
            lines.append("```json")
            lines.append(json.dumps(tool_input, indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append(f"- **👁️ Observación de la Herramienta (Observation):**")
            lines.append("```json")
            lines.append(json.dumps(obs, indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")

    lines.extend([
        "#### 🏁 Dictamen Final de la Propuesta",
        f"- **Estado:** `{assessment.status.value}`",
        f"- **¿Cubierto por Póliza?:** `{'Sí' if assessment.is_covered else 'No'}`",
        f"- **Resumen de Cobertura:** {assessment.coverage_summary}",
        f"- **Indemnización Neta Calculada:** `{assessment.net_payout:.2f} €` (Franquicia: `{assessment.deductible:.2f} €`)",
        f"- **Justificación:** {assessment.reasoning}",
        f"- **Recomendación Gestor:** {assessment.recommendation}",
    ])

    return "\n".join(lines)


def format_reasoning_flow_mermaid(assessment: ClaimAssessment) -> str:
    """Generate a Mermaid flowchart visualizing the agent reasoning path.

    Args:
        assessment: Evaluated ClaimAssessment instance.

    Returns:
        Mermaid diagram code block string.
    """
    mermaid_lines: List[str] = [
        "```mermaid",
        "flowchart TD",
        f'    Start(["📥 Reclamación {assessment.claim_id}"]) --> PII["🛡️ Filtro PII Anonimizado"]',
        '    PII --> Agent["🤖 Agente ReAct (Allianz Evaluator)"]',
    ]

    prev_node = "Agent"
    for idx, step in enumerate(assessment.intermediate_steps, start=1):
        tool = step.get("tool", f"tool_{idx}")
        action_node = f"Step{idx}Action"
        obs_node = f"Step{idx}Obs"

        if "coverage" in tool.lower():
            label = "1. check_policy_coverage"
        elif "calculate" in tool.lower() or "repair" in tool.lower():
            label = "2. calculate_repair_estimate"
        else:
            label = f"{idx}. {tool}"

        mermaid_lines.append(f'    {prev_node} -->|Invocación| {action_node}["🛠️ {label}"]')
        mermaid_lines.append(f'    {action_node} -->|Retorno| {obs_node}["📊 Resultado {label}"]')
        prev_node = obs_node

    status_str = assessment.status.value
    payout_str = f"{assessment.net_payout:.2f} €"
    final_node = "FinalDecision"

    if assessment.is_covered:
        mermaid_lines.append(
            f'    {prev_node} --> {final_node}["✅ Dictamen: {status_str}<br/>Pago Neto: {payout_str}"]'
        )
    elif "peritaje" in status_str.lower():
        mermaid_lines.append(
            f'    {prev_node} --> {final_node}["⚠️ Dictamen: {status_str}<br/>Derivación a Perito"]'
        )
    else:
        mermaid_lines.append(
            f'    {prev_node} --> {final_node}["❌ Dictamen: {status_str}<br/>Sin Cobertura (0.00 €)"]'
        )

    mermaid_lines.append(
        f'    {final_node} --> HITL["👤 Human-in-the-loop (Gestor Allianz)"]'
    )
    mermaid_lines.append("```")

    return "\n".join(mermaid_lines)


def export_audit_trail_dict(assessment: ClaimAssessment) -> Dict[str, Any]:
    """Export complete audit bundle as a dictionary suitable for JSON archiving.

    Args:
        assessment: ClaimAssessment model.

    Returns:
        Structured audit dictionary.
    """
    return {
        "claim_id": assessment.claim_id,
        "created_at": assessment.created_at.isoformat(),
        "status": assessment.status.value,
        "is_covered": assessment.is_covered,
        "coverage_summary": assessment.coverage_summary,
        "net_payout": assessment.net_payout,
        "deductible": assessment.deductible,
        "cost_breakdown": assessment.cost_breakdown.model_dump() if assessment.cost_breakdown else None,
        "reasoning": assessment.reasoning,
        "recommendation": assessment.recommendation,
        "metrics": assessment.metrics.model_dump(),
        "intermediate_steps": assessment.intermediate_steps,
    }
