"""Data models and schemas for EU AI Act compliance and governance auditing (US-08).

Defines structures for regulatory risk classification, human-in-the-loop oversight,
transparency accreditation, data governance, and automated technical audit sheets.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskCategory(str, Enum):
    """Risk tier classification according to EU AI Act (Regulation EU 2024/1689)."""

    UNACCEPTABLE_RISK = "Riesgo Inaceptable (Prohibido)"
    HIGH_RISK = "Alto Riesgo (Anexo III)"
    SPECIFIC_TRANSPARENCY_RISK = "Riesgo de Transparencia Específico"
    MINIMAL_RISK = "Riesgo Mínimo o Nulo"


class ComplianceCheckStatus(str, Enum):
    """Status evaluation for an individual compliance check."""

    COMPLIANT = "Cumple"
    PARTIALLY_COMPLIANT = "Parcialmente Conforme"
    NON_COMPLIANT = "No Conforme"
    NOT_APPLICABLE = "No Aplica"


class ComplianceCheckItem(BaseModel):
    """Detailed record of an individual regulatory requirement evaluated under EU AI Act."""

    model_config = ConfigDict(populate_by_name=True)

    article_reference: str = Field(
        ...,
        description="EU AI Act article or regulatory framework reference (e.g. Art. 14 Supervisión Humana).",
    )
    name: str = Field(
        ...,
        description="Short descriptive name of the compliance control.",
    )
    status: ComplianceCheckStatus = Field(
        ...,
        description="Evaluation result for this specific requirement.",
    )
    description: str = Field(
        ...,
        description="Regulatory rationale and standard requirement.",
    )
    evidence: str = Field(
        ...,
        description="Specific technical and operational evidence gathered from execution.",
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured telemetry, metrics, or technical indicators supporting the evidence.",
    )


class RiskClassification(BaseModel):
    """Risk classification details under EU AI Act Annex III."""

    model_config = ConfigDict(populate_by_name=True)

    category: RiskCategory = Field(
        default=RiskCategory.HIGH_RISK,
        description="Assigned risk category.",
    )
    annex_reference: str = Field(
        default="Anexo III, Punto 5(a) - Acceso a servicios privados esenciales y prestaciones públicas (Evaluación de riesgos y precios/siniestros en seguros)",
        description="Legal reference within the EU AI Act.",
    )
    justification: str = Field(
        ...,
        description="Technical and legal justification for the risk classification.",
    )
    applicable_mandatory_requirements: List[str] = Field(
        default_factory=lambda: [
            "Art. 9: Sistema de gestión de riesgos continuo.",
            "Art. 10: Gobernanza de datos y mitigación de sesgos/privacidad.",
            "Art. 11: Documentación técnica y ficha de conformidad previa al despliegue.",
            "Art. 12: Registro automático de eventos y trazabilidad (Logging).",
            "Art. 13: Transparencia y suministro de información a los operadores.",
            "Art. 14: Supervisión humana efectiva (Human-in-the-Loop).",
            "Art. 15: Precisión, robustez técnica y ciberseguridad.",
        ],
        description="List of mandatory EU AI Act articles applicable to this high-risk classification.",
    )


class HumanInTheLoopAudit(BaseModel):
    """Verification that the AI Agent operates strictly under human oversight (Art. 14)."""

    model_config = ConfigDict(populate_by_name=True)

    is_proposal: bool = Field(
        default=True,
        description="Guarantees that the decision produced is an assisted proposal, not an autonomous settlement.",
    )
    human_validation_required: bool = Field(
        default=True,
        description="Flag enforcing mandatory sign-off by human claim handler before payout or denial.",
    )
    recommendation_summary: str = Field(
        ...,
        description="Recommended action provided for human review.",
    )
    override_mechanism: str = Field(
        default="El gestor de siniestros de Allianz mantiene control total para modificar, aprobar o revocar la propuesta del agente en cualquier momento.",
        description="Description of human override and dispute capability.",
    )
    status: ComplianceCheckStatus = Field(
        default=ComplianceCheckStatus.COMPLIANT,
        description="Overall Human-in-the-Loop compliance status.",
    )


class TransparencyAudit(BaseModel):
    """Verification of system transparency, explainability, and record-keeping (Art. 12 & Art. 13)."""

    model_config = ConfigDict(populate_by_name=True)

    has_traceability_logs: bool = Field(
        ...,
        description="True if intermediate thought steps and tool invocations were recorded.",
    )
    reasoning_provided: bool = Field(
        ...,
        description="True if detailed, understandable natural language justification is present.",
    )
    tools_executed: List[str] = Field(
        default_factory=list,
        description="List of deterministic tools called by the agent during resolution.",
    )
    execution_time_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Audited execution latency in seconds.",
    )
    total_tokens_consumed: int = Field(
        default=0,
        ge=0,
        description="Total tokens consumed in LLM reasoning.",
    )
    model_name: str = Field(
        default="gpt-4o-mini",
        description="Language model utilized.",
    )
    status: ComplianceCheckStatus = Field(
        default=ComplianceCheckStatus.COMPLIANT,
        description="Transparency compliance status.",
    )


class DataPrivacyAudit(BaseModel):
    """Verification of data governance, quality, and privacy by design (Art. 10 & GDPR)."""

    model_config = ConfigDict(populate_by_name=True)

    pii_masking_applied: bool = Field(
        ...,
        description="True if sensitive PII was anonymized before invoking external LLM APIs.",
    )
    detected_entities_count: int = Field(
        default=0,
        ge=0,
        description="Number of PII entities detected and masked.",
    )
    gdpr_compliance_status: str = Field(
        default="Cumplimiento con RGPD (Reglamento UE 2016/679) mediante minimización y pseudoanonimización previa a inferencia.",
        description="GDPR compliance statement.",
    )
    status: ComplianceCheckStatus = Field(
        default=ComplianceCheckStatus.COMPLIANT,
        description="Data governance and privacy compliance status.",
    )


class EUAIActComplianceReport(BaseModel):
    """Complete technical compliance sheet and regulatory audit report under EU AI Act."""

    model_config = ConfigDict(populate_by_name=True)

    report_id: str = Field(
        default_factory=lambda: f"AUD-EUAI-{uuid4().hex[:8].upper()}",
        description="Unique identifier for this compliance audit record.",
    )
    claim_id: str = Field(
        ...,
        description="Associated claim identifier.",
    )
    system_name: str = Field(
        default="GuardSeguro AI - Agente Evaluador de Siniestros (Allianz Spain CoE)",
        description="Name of the evaluated AI system.",
    )
    assessed_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the compliance audit was generated.",
    )
    risk_classification: RiskClassification = Field(
        ...,
        description="Risk category and legal justification under Annex III.",
    )
    human_in_the_loop: HumanInTheLoopAudit = Field(
        ...,
        description="Verification of Art. 14 Human Oversight.",
    )
    transparency_audit: TransparencyAudit = Field(
        ...,
        description="Verification of Art. 12 & 13 Transparency and Record-Keeping.",
    )
    privacy_audit: DataPrivacyAudit = Field(
        ...,
        description="Verification of Art. 10 Data Governance and Privacy.",
    )
    checks: List[ComplianceCheckItem] = Field(
        default_factory=list,
        description="Itemized compliance checklist across all evaluated articles.",
    )
    compliance_score: float = Field(
        default=100.0,
        ge=0.0,
        le=100.0,
        description="Global compliance score percentage (0-100%).",
    )
    is_certified: bool = Field(
        default=True,
        description="True if the assessment meets all mandatory EU AI Act High-Risk standards.",
    )

    @model_validator(mode="after")
    def compute_overall_certification(self) -> "EUAIActComplianceReport":
        """Compute compliance score and certification status from individual checks."""
        if not self.checks:
            return self

        total_checks = len(self.checks)
        compliant_count = sum(1 for c in self.checks if c.status == ComplianceCheckStatus.COMPLIANT)
        partial_count = sum(1 for c in self.checks if c.status == ComplianceCheckStatus.PARTIALLY_COMPLIANT)

        score = ((compliant_count * 1.0) + (partial_count * 0.5)) / total_checks * 100.0
        self.compliance_score = round(score, 1)

        # High risk certification fails if any check is NON_COMPLIANT
        has_non_compliant = any(c.status == ComplianceCheckStatus.NON_COMPLIANT for c in self.checks)
        self.is_certified = (not has_non_compliant) and (self.compliance_score >= 80.0)

        return self
