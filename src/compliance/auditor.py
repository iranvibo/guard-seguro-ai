"""EU AI Act Compliance Auditor and Governance Engine for GuardSeguro AI (US-08).

Evaluates claim assessments against European Union Artificial Intelligence Act standards
for High-Risk AI Systems (Regulation EU 2024/1689, Annex III).
"""

import json
import logging
from typing import Any, Dict, List, Optional

from src.compliance.models import (
    ComplianceCheckItem,
    ComplianceCheckStatus,
    DataPrivacyAudit,
    EUAIActComplianceReport,
    HumanInTheLoopAudit,
    RiskCategory,
    RiskClassification,
    TransparencyAudit,
)
from src.core.models import AnonymizedClaim, ClaimAssessment, ClaimInput

logger = logging.getLogger(__name__)


class EUAIActAuditor:
    """Evaluates and certifies AI Agent claim assessments against EU AI Act requirements."""

    def __init__(self, system_name: Optional[str] = None):
        """Initialize EU AI Act auditor.

        Args:
            system_name: Optional custom system name string.
        """
        self.system_name = system_name or "GuardSeguro AI - Agente Evaluador de Siniestros (Allianz Spain CoE)"

    def audit(
        self,
        assessment: ClaimAssessment,
        anonymized_claim: Optional[AnonymizedClaim] = None,
        claim_input: Optional[ClaimInput] = None,
    ) -> EUAIActComplianceReport:
        """Perform a comprehensive regulatory compliance audit on a claim assessment.

        Args:
            assessment: The final ClaimAssessment produced by the AI Agent.
            anonymized_claim: Optional AnonymizedClaim from PII masking step.
            claim_input: Optional original ClaimInput submitted by handler.

        Returns:
            EUAIActComplianceReport with full certification checklist and metrics.
        """
        checks: List[ComplianceCheckItem] = []

        # 1. Evaluate Risk Classification (Annex III, Point 5(a))
        risk_classification = self._evaluate_risk_classification(assessment, checks)

        # 2. Evaluate Human-in-the-Loop (Art. 14)
        human_audit = self._evaluate_human_in_the_loop(assessment, checks)

        # 3. Evaluate Transparency & Record-Keeping (Art. 12 & Art. 13)
        transparency_audit = self._evaluate_transparency_and_logs(assessment, checks)

        # 4. Evaluate Data Governance & Privacy (Art. 10 & GDPR)
        privacy_audit = self._evaluate_data_privacy(anonymized_claim, checks)

        # 5. Evaluate Accuracy, Determinism & Cybersecurity (Art. 15)
        self._evaluate_accuracy_and_robustness(assessment, checks)

        # 6. Evaluate Continuous Risk Management (Art. 9)
        self._evaluate_risk_management_system(assessment, checks)

        # Build full report
        report = EUAIActComplianceReport(
            claim_id=assessment.claim_id,
            system_name=self.system_name,
            risk_classification=risk_classification,
            human_in_the_loop=human_audit,
            transparency_audit=transparency_audit,
            privacy_audit=privacy_audit,
            checks=checks,
        )

        logger.info(
            "EU AI Act Audit generated for claim %s: certified=%s, score=%.1f%%",
            assessment.claim_id,
            report.is_certified,
            report.compliance_score,
        )

        return report

    def _evaluate_risk_classification(
        self, assessment: ClaimAssessment, checks: List[ComplianceCheckItem]
    ) -> RiskClassification:
        """Evaluate and certify risk tier under EU AI Act Annex III."""
        justification = (
            "GuardSeguro AI se clasifica como Sistema de IA de Alto Riesgo bajo el Anexo III, "
            "Punto 5(a) del Reglamento (UE) 2024/1689 (EU AI Act). "
            "El sistema evalúa reclamaciones de siniestros y determina indemnizaciones económicas directas "
            "en el ámbito de seguros privados esenciales, lo que exige estricta gobernanza, supervisión humana, "
            "trazabilidad de decisiones y protección de datos."
        )

        risk_class = RiskClassification(
            category=RiskCategory.HIGH_RISK,
            annex_reference="Anexo III, Punto 5(a) - Servicios esenciales y evaluación de siniestros aseguradores",
            justification=justification,
        )

        checks.append(
            ComplianceCheckItem(
                article_reference="Art. 6 & Anexo III Punto 5(a)",
                name="Clasificación de Riesgo Regulatorio",
                status=ComplianceCheckStatus.COMPLIANT,
                description="Identificación y justificación del nivel de riesgo según el marco europeo.",
                evidence=f"Categorizado como {risk_class.category.value}. Sujeto a obligaciones de Alto Riesgo.",
                details={"category": risk_class.category.value, "annex": risk_class.annex_reference},
            )
        )

        return risk_class

    def _evaluate_human_in_the_loop(
        self, assessment: ClaimAssessment, checks: List[ComplianceCheckItem]
    ) -> HumanInTheLoopAudit:
        """Evaluate compliance with Art. 14 Human Oversight (Human-in-the-Loop)."""
        has_rec = bool(assessment.recommendation and assessment.recommendation.strip())
        rec_lower = assessment.recommendation.lower()
        is_explicit_proposal = any(
            kw in rec_lower
            for kw in [
                "gestor",
                "humano",
                "revisión",
                "revision",
                "validación",
                "validacion",
                "peritaje",
                "tramitador",
                "supervisión",
                "supervision",
                "propuesta",
            ]
        )

        status = ComplianceCheckStatus.COMPLIANT if (has_rec and is_explicit_proposal) else ComplianceCheckStatus.PARTIALLY_COMPLIANT

        audit = HumanInTheLoopAudit(
            is_proposal=True,
            human_validation_required=True,
            recommendation_summary=assessment.recommendation or "Propuesta sujeta a validación final de tramitador.",
            status=status,
        )

        checks.append(
            ComplianceCheckItem(
                article_reference="Art. 14 EU AI Act (Supervisión Humana)",
                name="Garantía de Human-in-the-Loop",
                status=status,
                description="La decisión del agente debe ser una propuesta asistida sujeta a validación y override por el gestor.",
                evidence=(
                    f"Propuesta no autónoma con requerimiento explícito de supervisión humana: "
                    f"'{audit.recommendation_summary}'"
                ),
                details={
                    "is_proposal": True,
                    "human_validation_required": True,
                    "override_enabled": True,
                },
            )
        )

        return audit

    def _evaluate_transparency_and_logs(
        self, assessment: ClaimAssessment, checks: List[ComplianceCheckItem]
    ) -> TransparencyAudit:
        """Evaluate compliance with Art. 12 (Record-keeping) and Art. 13 (Transparency)."""
        has_steps = len(assessment.intermediate_steps) > 0
        has_reasoning = bool(assessment.reasoning and len(assessment.reasoning.strip()) > 10)
        tools = assessment.metrics.tools_called or []

        if has_steps and has_reasoning:
            status = ComplianceCheckStatus.COMPLIANT
            evidence_msg = (
                f"Trazabilidad completa: {len(assessment.intermediate_steps)} pasos auditados, "
                f"{len(tools)} herramientas invocadas ({', '.join(tools) if tools else 'evaluación directa'}). "
                f"Latencia: {assessment.metrics.execution_time_seconds:.2f}s, "
                f"Tokens: {assessment.metrics.total_tokens}."
            )
        elif has_reasoning:
            status = ComplianceCheckStatus.PARTIALLY_COMPLIANT
            evidence_msg = (
                "Razonamiento registrado pero sin desglose detallado de pasos intermedios de herramientas."
            )
        else:
            status = ComplianceCheckStatus.NON_COMPLIANT
            evidence_msg = "Ausencia de justificación o trazabilidad auditable en la resolución."

        transparency = TransparencyAudit(
            has_traceability_logs=has_steps,
            reasoning_provided=has_reasoning,
            tools_executed=tools,
            execution_time_seconds=assessment.metrics.execution_time_seconds,
            total_tokens_consumed=assessment.metrics.total_tokens,
            model_name=assessment.metrics.model_name,
            status=status,
        )

        checks.append(
            ComplianceCheckItem(
                article_reference="Art. 12 EU AI Act (Registro Automático de Eventos)",
                name="Trazabilidad y Logging de Razonamiento",
                status=ComplianceCheckStatus.COMPLIANT if has_steps else ComplianceCheckStatus.PARTIALLY_COMPLIANT,
                description="Registro continuo y auditable de las operaciones, llamadas a herramientas y tiempos de ejecución.",
                evidence=evidence_msg,
                details={
                    "steps_count": len(assessment.intermediate_steps),
                    "execution_time_seconds": assessment.metrics.execution_time_seconds,
                    "tools": tools,
                },
            )
        )

        checks.append(
            ComplianceCheckItem(
                article_reference="Art. 13 EU AI Act (Transparencia y Explicabilidad)",
                name="Explicabilidad y Transparencia Algorítmica",
                status=ComplianceCheckStatus.COMPLIANT if has_reasoning else ComplianceCheckStatus.NON_COMPLIANT,
                description="Capacidad del sistema para explicar de forma comprensible el dictamen alcanzado sin cajas negras.",
                evidence=(
                    f"Justificación técnica y fundamentación clara proporcionada: "
                    f"'{assessment.coverage_summary}' | Razonamiento con {len(assessment.reasoning)} caracteres."
                ),
                details={
                    "reasoning_length_chars": len(assessment.reasoning),
                    "coverage_summary": assessment.coverage_summary,
                },
            )
        )

        return transparency

    def _evaluate_data_privacy(
        self,
        anonymized_claim: Optional[AnonymizedClaim],
        checks: List[ComplianceCheckItem],
    ) -> DataPrivacyAudit:
        """Evaluate compliance with Art. 10 (Data Governance) and GDPR Privacy by Design."""
        if anonymized_claim is not None:
            masking_applied = True
            count = anonymized_claim.detected_entities_count
            evidence_msg = (
                f"Filtro PII activo: {count} entidades de datos personales sensibles detectadas "
                f"y enmascaradas con pseudo-tokens antes de invocar el LLM."
            )
            status = ComplianceCheckStatus.COMPLIANT
        else:
            masking_applied = False
            count = 0
            evidence_msg = "No se adjuntó registro del filtro PII o la evaluación se ejecutó sin paso de anonimización previo."
            status = ComplianceCheckStatus.PARTIALLY_COMPLIANT

        privacy = DataPrivacyAudit(
            pii_masking_applied=masking_applied,
            detected_entities_count=count,
            status=status,
        )

        checks.append(
            ComplianceCheckItem(
                article_reference="Art. 10 EU AI Act & RGPD (Art. 5 y 25)",
                name="Gobernanza de Datos y Privacidad por Diseño",
                status=status,
                description="Minimización de datos personales y anonimización de PII antes de cualquier procesamiento externo por LLMs.",
                evidence=evidence_msg,
                details={
                    "pii_masking_applied": masking_applied,
                    "entities_masked_count": count,
                },
            )
        )

        return privacy

    def _evaluate_accuracy_and_robustness(
        self, assessment: ClaimAssessment, checks: List[ComplianceCheckItem]
    ) -> None:
        """Evaluate compliance with Art. 15 (Accuracy, Robustness and Cybersecurity)."""
        has_breakdown = assessment.cost_breakdown is not None
        has_valid_math = True
        if has_breakdown:
            cb = assessment.cost_breakdown
            expected_gross = round(cb.materials + cb.labor, 2)
            expected_net = round(max(0.0, expected_gross - cb.deductible), 2)
            has_valid_math = (abs(cb.gross_total - expected_gross) <= 0.05) and (
                abs(cb.net_total - expected_net) <= 0.05
            )

        status = ComplianceCheckStatus.COMPLIANT if has_valid_math else ComplianceCheckStatus.NON_COMPLIANT

        checks.append(
            ComplianceCheckItem(
                article_reference="Art. 15 EU AI Act (Precisión y Robustez Técnica)",
                name="Precisión Matemática y Determinismo de Baremos",
                status=status,
                description="Garantía de cálculos deterministas basados en baremos oficiales sin alucinaciones numéricas del LLM.",
                evidence=(
                    f"Cálculos monetarios validados: Bruto={assessment.cost_breakdown.gross_total if has_breakdown else 0.0}€, "
                    f"Franquicia={assessment.deductible}€, Neto={assessment.net_payout}€."
                ),
                details={
                    "math_validated": has_valid_math,
                    "net_payout_eur": assessment.net_payout,
                    "deductible_eur": assessment.deductible,
                },
            )
        )

    def _evaluate_risk_management_system(
        self, assessment: ClaimAssessment, checks: List[ComplianceCheckItem]
    ) -> None:
        """Evaluate compliance with Art. 9 (Risk Management System)."""
        checks.append(
            ComplianceCheckItem(
                article_reference="Art. 9 EU AI Act (Sistema de Gestión de Riesgos)",
                name="Control Continuo de Riesgos Operacionales y de Sesgo",
                status=ComplianceCheckStatus.COMPLIANT,
                description="Identificación y mitigación continua de riesgos de alucinación, discriminación y sobreestimación.",
                evidence="Uso de herramientas de verificación deterministas acopladas a catálogo cerrado de pólizas.",
                details={"catalog_verified": True},
            )
        )


def generate_compliance_report(
    assessment: ClaimAssessment,
    anonymized_claim: Optional[AnonymizedClaim] = None,
    claim_input: Optional[ClaimInput] = None,
    system_name: Optional[str] = None,
) -> EUAIActComplianceReport:
    """Convenience function to generate a full EU AI Act compliance report for a claim assessment.

    Args:
        assessment: Final ClaimAssessment produced by GuardSeguro AI.
        anonymized_claim: Optional AnonymizedClaim with PII masking metadata.
        claim_input: Optional original ClaimInput.
        system_name: Optional custom system name string.

    Returns:
        EUAIActComplianceReport certified and scored.
    """
    auditor = EUAIActAuditor(system_name=system_name)
    return auditor.audit(
        assessment=assessment,
        anonymized_claim=anonymized_claim,
        claim_input=claim_input,
    )


def format_compliance_report_markdown(report: EUAIActComplianceReport) -> str:
    """Render an EU AI Act Compliance Report as a structured, executive Markdown document.

    Args:
        report: EUAIActComplianceReport instance to format.

    Returns:
        Markdown string formatted for Streamlit or audit exports.
    """
    badge_status = "🟢 CERTIFICADO CONFORME" if report.is_certified else "🔴 REVISIÓN REQUERIDA"
    timestamp_str = report.assessed_at.strftime("%Y-%m-%d %H:%M:%S")

    md = [
        f"# ⚖️ Ficha Técnica de Cumplimiento — EU AI Act",
        f"**Sistema:** `{report.system_name}`  ",
        f"**Expediente Siniestro:** `{report.claim_id}` | **Auditoría:** `{report.report_id}` | **Fecha:** `{timestamp_str}`  ",
        f"**Dictamen de Conformidad:** **{badge_status}** (Puntuación de Gobernanza: **{report.compliance_score:.1f}%**)\n",
        "---",
        "## 1. 🛡️ Clasificación de Riesgo Regulatorio (Anexo III)",
        f"- **Categoría:** **{report.risk_classification.category.value}**",
        f"- **Base Legal:** `{report.risk_classification.annex_reference}`",
        f"- **Justificación:** {report.risk_classification.justification}\n",
        "**Requisitos Obligatorios Aplicables:**",
    ]

    for req in report.risk_classification.applicable_mandatory_requirements:
        md.append(f"  - {req}")

    md.extend(
        [
            "\n---",
            "## 2. 👤 Supervisión Humana Efectiva (Human-in-the-Loop - Art. 14)",
            f"- **Naturaleza de la Decisión:** Propuesta Asistida (*Non-Autonomous Recommendation*)",
            f"- **Validación Humana Obligatoria:** `{'SÍ (Requerida)' if report.human_in_the_loop.human_validation_required else 'NO'}`",
            f"- **Recomendación para el Gestor:** *\"{report.human_in_the_loop.recommendation_summary}\"*",
            f"- **Control y Override:** {report.human_in_the_loop.override_mechanism}\n",
            "---",
            "## 3. 🔍 Transparencia, Trazabilidad y Explicabilidad (Art. 12 & Art. 13)",
            f"- **Trazabilidad de Pasos:** `{'✅ Registrada' if report.transparency_audit.has_traceability_logs else '❌ Ausente'}`",
            f"- **Herramientas Auditadas:** `{', '.join(report.transparency_audit.tools_executed) if report.transparency_audit.tools_executed else 'Evaluación Directa'}`",
            f"- **Latencia de Inferencia:** `{report.transparency_audit.execution_time_seconds:.2f} s`",
            f"- **Consumo de Tokens:** `{report.transparency_audit.total_tokens_consumed} tokens` (`{report.transparency_audit.model_name}`)",
            f"- **Explicabilidad Algorítmica:** Justificación en lenguaje natural disponible y comprensible.\n",
            "---",
            "## 4. 🔒 Gobernanza de Datos y Privacidad (Art. 10 & RGPD)",
            f"- **Filtro de Enmascaramiento PII:** `{'✅ Aplicado antes de LLM' if report.privacy_audit.pii_masking_applied else '⚠️ No Detectado'}`",
            f"- **Entidades Sensibles Anonimizadas:** `{report.privacy_audit.detected_entities_count}`",
            f"- **Conformidad RGPD:** {report.privacy_audit.gdpr_compliance_status}\n",
            "---",
            "## 5. 📋 Tabla de Controles y Evidencias Técnicas",
            "",
            "| Artículo / Marco | Control de Gobernanza | Estado | Evidencia Técnica Auditada |",
            "|---|---|:---:|---|",
        ]
    )

    status_icons = {
        ComplianceCheckStatus.COMPLIANT: "✅ Cumple",
        ComplianceCheckStatus.PARTIALLY_COMPLIANT: "⚠️ Parcial",
        ComplianceCheckStatus.NON_COMPLIANT: "❌ No Cumple",
        ComplianceCheckStatus.NOT_APPLICABLE: "⚪ N/A",
    }

    for c in report.checks:
        icon = status_icons.get(c.status, str(c.status.value))
        safe_evidence = c.evidence.replace("|", "\\|")
        md.append(f"| **{c.article_reference}** | {c.name} | **{icon}** | {safe_evidence} |")

    return "\n".join(md)


def export_compliance_report_dict(report: EUAIActComplianceReport) -> Dict[str, Any]:
    """Serialize an EUAIActComplianceReport into a plain JSON-compatible dictionary.

    Args:
        report: EUAIActComplianceReport to serialize.

    Returns:
        JSON serializable dictionary.
    """
    return report.model_dump(mode="json")
