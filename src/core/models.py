"""Core domain models and data schemas for GuardSeguro AI.

Provides strongly typed Pydantic v2 data models for claims, PII anonymization,
coverage evaluation, repair cost breakdowns, and final assessments.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CoverageStatus(str, Enum):
    """Possible outcomes for claim coverage assessment."""

    APPROVED = "Aprobado"
    DENIED = "Denegado"
    REQUIRES_EXPERT = "Requiere Peritaje"


class DamageSeverity(str, Enum):
    """Standardized damage severity levels for cost calculations."""

    LIGHT = "Leve"
    MODERATE = "Moderado"
    SEVERE = "Grave"


class ClaimInput(BaseModel):
    """Initial claim data submitted by insurance claim handler."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    claim_id: str = Field(
        default_factory=lambda: f"CLM-{uuid4().hex[:8].upper()}",
        description="Unique identifier for the claim (e.g., CLM-A1B2C3D4).",
    )
    raw_text: str = Field(
        ...,
        min_length=5,
        description="Raw description of the claim entered by the handler, potentially containing PII.",
    )
    incident_date: datetime = Field(
        default_factory=datetime.now,
        description="Date and time when the incident occurred or was reported.",
    )
    policy_id: Optional[str] = Field(
        default=None,
        description="Optional policy number or reference associated with the claim.",
    )
    policy_type: str = Field(
        default="Auto",
        description="Type of insurance policy (e.g. Auto, Hogar).",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional optional metadata or context.",
    )

    @field_validator("raw_text")
    @classmethod
    def validate_raw_text_not_blank(cls, v: str) -> str:
        """Ensure raw text is not just whitespace."""
        if not v.strip():
            raise ValueError("Claim raw text cannot be empty or blank.")
        return v.strip()


class AnonymizedClaim(BaseModel):
    """Claim representation after PII detection and masking."""

    model_config = ConfigDict(populate_by_name=True)

    claim_id: str = Field(
        ...,
        description="Unique claim identifier linking back to ClaimInput.",
    )
    original_text: str = Field(
        ...,
        description="Original text before anonymization.",
    )
    anonymized_text: str = Field(
        ...,
        description="Anonymized text with sensitive PII replaced by pseudo-tokens (e.g. [PERSONA_1]).",
    )
    pii_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Secure mapping dictionary: {placeholder: original_value}.",
    )
    detected_entities_count: int = Field(
        default=0,
        description="Total count of PII entities detected and masked.",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when anonymization was executed.",
    )

    @model_validator(mode="before")
    @classmethod
    def compute_entities_count(cls, data: Any) -> Any:
        """Automatically compute entity count if not explicitly set."""
        if isinstance(data, dict):
            mapping = data.get("pii_mapping", {})
            if "detected_entities_count" not in data or data["detected_entities_count"] == 0:
                data["detected_entities_count"] = len(mapping)
        return data


class CoverageCheckResult(BaseModel):
    """Structured result returned by the policy coverage verification tool."""

    model_config = ConfigDict(populate_by_name=True)

    is_covered: bool = Field(
        ...,
        description="True if the incident or damage type is covered by policy terms.",
    )
    coverage_type: str = Field(
        ...,
        description="Identified coverage category (e.g. Rotura de lunas, Fenómenos atmosféricos, Granizo).",
    )
    conditions: str = Field(
        ...,
        description="Specific policy terms, exclusions or limitations applicable.",
    )
    standard_deductible: float = Field(
        default=0.0,
        ge=0.0,
        description="Standard deductible applicable to this coverage type in EUR (€).",
    )


class CostBreakdown(BaseModel):
    """Detailed itemization of repair costs and deductible deductions."""

    model_config = ConfigDict(populate_by_name=True)

    materials: float = Field(
        ...,
        ge=0.0,
        description="Cost of spare parts and materials in EUR (€).",
    )
    labor: float = Field(
        ...,
        ge=0.0,
        description="Cost of repair labor (mano de obra) in EUR (€).",
    )
    gross_total: float = Field(
        default=0.0,
        ge=0.0,
        description="Total gross repair cost before deductible (materials + labor).",
    )
    deductible: float = Field(
        default=0.0,
        ge=0.0,
        description="Applicable policy deductible subtracted from payment in EUR (€).",
    )
    net_total: float = Field(
        default=0.0,
        ge=0.0,
        description="Final payout payable by GuardSeguro (gross_total - deductible, minimum 0).",
    )

    @model_validator(mode="after")
    def calculate_totals(self) -> "CostBreakdown":
        """Ensure gross and net totals match materials, labor and deductible mathematically."""
        calculated_gross = round(self.materials + self.labor, 2)
        if self.gross_total == 0.0 or abs(self.gross_total - calculated_gross) > 0.01:
            self.gross_total = calculated_gross

        calculated_net = round(max(0.0, self.gross_total - self.deductible), 2)
        if self.net_total == 0.0 or abs(self.net_total - calculated_net) > 0.01:
            self.net_total = calculated_net

        return self


class ExecutionMetrics(BaseModel):
    """Observability and execution metrics for auditing agent reasoning and resource consumption."""

    model_config = ConfigDict(populate_by_name=True)

    execution_time_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Total execution time in seconds (latency).",
    )
    prompt_tokens: int = Field(
        default=0,
        ge=0,
        description="Tokens consumed by the prompt/system input.",
    )
    completion_tokens: int = Field(
        default=0,
        ge=0,
        description="Tokens generated by the model completion.",
    )
    total_tokens: int = Field(
        default=0,
        ge=0,
        description="Total tokens consumed across all LLM calls (prompt + completion).",
    )
    estimated_cost_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated monetary cost in USD based on model pricing.",
    )
    model_name: str = Field(
        default="gpt-4o-mini",
        description="Model identifier utilized for evaluation.",
    )
    tools_called: List[str] = Field(
        default_factory=list,
        description="Sequence of tool names executed during evaluation.",
    )
    tools_count: int = Field(
        default=0,
        ge=0,
        description="Total count of tool executions.",
    )

    @model_validator(mode="before")
    @classmethod
    def sync_token_and_tool_counts(cls, data: Any) -> Any:
        """Ensure total tokens and tools count are synchronized."""
        if isinstance(data, dict):
            p_tok = data.get("prompt_tokens", 0)
            c_tok = data.get("completion_tokens", 0)
            t_tok = data.get("total_tokens", 0)
            if t_tok == 0 and (p_tok > 0 or c_tok > 0):
                data["total_tokens"] = p_tok + c_tok
            tools = data.get("tools_called", [])
            if "tools_count" not in data or data["tools_count"] == 0:
                data["tools_count"] = len(tools)
        return data


class ToolCallTrace(BaseModel):
    """Detailed audit trace record for a single tool call in ReAct loop."""

    model_config = ConfigDict(populate_by_name=True)

    step_number: int = Field(
        ...,
        ge=1,
        description="Sequential step index.",
    )
    tool: str = Field(
        ...,
        description="Name of the tool invoked.",
    )
    tool_input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Exact parameters supplied to the tool.",
    )
    observation: Any = Field(
        default=None,
        description="Output returned by the tool.",
    )
    thought: str = Field(
        default="",
        description="Reasoning or thought log preceding tool call.",
    )
    execution_time_seconds: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Execution duration of this tool step.",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of tool call execution.",
    )


class ClaimAssessment(BaseModel):
    """Final assessment resolution produced by the AI Agent."""

    model_config = ConfigDict(populate_by_name=True)

    claim_id: str = Field(
        ...,
        description="Identifier of the assessed claim.",
    )
    status: CoverageStatus = Field(
        ...,
        description="Final claim disposition: Aprobado, Denegado, or Requiere Peritaje.",
    )
    is_covered: bool = Field(
        ...,
        description="Binary flag indicating whether coverage was granted.",
    )
    coverage_summary: str = Field(
        ...,
        description="Executive summary of the coverage analysis.",
    )
    cost_breakdown: Optional[CostBreakdown] = Field(
        default=None,
        description="Itemized cost breakdown if claim is covered or evaluated.",
    )
    deductible: float = Field(
        default=0.0,
        ge=0.0,
        description="Franquicia aplicable en EUR (€).",
    )
    net_payout: float = Field(
        default=0.0,
        ge=0.0,
        description="Final net amount payable to client or repair shop in EUR (€).",
    )
    reasoning: str = Field(
        ...,
        description="Detailed, transparent reasoning justifying the decision.",
    )
    recommendation: str = Field(
        default="Revisión y validación por gestor humano requerida.",
        description="Recommended next step for human-in-the-loop claim handler.",
    )
    intermediate_steps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Audit trace of tools called, inputs, and intermediate thoughts.",
    )
    metrics: ExecutionMetrics = Field(
        default_factory=ExecutionMetrics,
        description="Execution and observability metrics (latency, token consumption, etc.).",
    )
    api_error: Optional[str] = Field(
        default=None,
        description="Error details if LLM API failed (e.g. invalid key, quota exhausted, network error).",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of assessment generation.",
    )

    @property
    def execution_metrics(self) -> ExecutionMetrics:
        """Convenience alias for metrics."""
        return self.metrics

    @model_validator(mode="after")
    def sync_payout_with_breakdown(self) -> "ClaimAssessment":
        """Synchronize net payout and deductible with cost breakdown when available."""
        if self.cost_breakdown is not None:
            self.deductible = self.cost_breakdown.deductible
            if self.is_covered:
                self.net_payout = self.cost_breakdown.net_total
            else:
                self.net_payout = 0.0
        elif not self.is_covered:
            self.net_payout = 0.0
        return self

