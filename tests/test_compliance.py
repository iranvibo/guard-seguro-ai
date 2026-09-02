"""Unit tests for EU AI Act Compliance and Governance Auditing module (US-08).

Tests risk classification under Annex III, human-in-the-loop validation,
transparency record-keeping, data privacy accreditation, and markdown export.
"""

from datetime import datetime
import pytest

from src.agent.claim_agent import evaluate_claim_with_compliance
from src.compliance.auditor import (
    EUAIActAuditor,
    export_compliance_report_dict,
    format_compliance_report_markdown,
    generate_compliance_report,
)
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
from src.core.models import (
    AnonymizedClaim,
    ClaimAssessment,
    ClaimInput,
    CostBreakdown,
    CoverageStatus,
    ExecutionMetrics,
)
from src.privacy.masker import anonymize_claim


@pytest.fixture
def mock_covered_assessment() -> ClaimAssessment:
    """Fixture providing a standard covered claim assessment."""
    cost_bd = CostBreakdown(
        materials=250.0,
        labor=120.0,
        gross_total=370.0,
        deductible=150.0,
        net_total=220.0,
    )
    metrics = ExecutionMetrics(
        execution_time_seconds=0.45,
        prompt_tokens=320,
        completion_tokens=180,
        total_tokens=500,
        estimated_cost_usd=0.00018,
        model_name="gpt-4o-mini",
        tools_called=["check_policy_coverage", "calculate_repair_estimate"],
        tools_count=2,
    )
    return ClaimAssessment(
        claim_id="CLM-TEST-001",
        status=CoverageStatus.APPROVED,
        is_covered=True,
        coverage_summary="Cobertura de Colisión y Daños Propios aplicable.",
        cost_breakdown=cost_bd,
        deductible=150.0,
        net_payout=220.0,
        reasoning="El impacto frontal contra otro vehículo está cubierto bajo la garantía de Colisión con franquicia de 150€.",
        recommendation="Propuesta de indemnización generada sujeta a validación final y pago por el gestor humano.",
        intermediate_steps=[
            {
                "tool": "check_policy_coverage",
                "tool_input": {"damage_type": "Colisión frontal"},
                "observation": {"is_covered": True, "coverage_type": "Colisión", "standard_deductible": 150.0},
            },
            {
                "tool": "calculate_repair_estimate",
                "tool_input": {"damage_type": "parachoques delantero", "severity": "Moderado", "deductible": 150.0},
                "observation": {"gross_total": 370.0, "net_total": 220.0},
            },
        ],
        metrics=metrics,
    )


@pytest.fixture
def mock_anonymized_claim() -> AnonymizedClaim:
    """Fixture providing an AnonymizedClaim with detected PII."""
    return AnonymizedClaim(
        claim_id="CLM-TEST-001",
        original_text="El cliente Carlos García DNI 12345678Z con matrícula 1234-XYZ tuvo un golpe en Barcelona.",
        anonymized_text="El cliente [PERSONA_1] DNI [DNI_1] con matrícula [MATRICULA_1] tuvo un golpe en [DIRECCION_1].",
        pii_mapping={
            "[PERSONA_1]": "Carlos García",
            "[DNI_1]": "12345678Z",
            "[MATRICULA_1]": "1234-XYZ",
            "[DIRECCION_1]": "Barcelona",
        },
        detected_entities_count=4,
    )


class TestRiskClassification:
    """Tests for EU AI Act Risk Tier classification (Annex III Point 5a)."""

    def test_risk_classification_is_high_risk(self, mock_covered_assessment: ClaimAssessment):
        report = generate_compliance_report(assessment=mock_covered_assessment)
        assert report.risk_classification.category == RiskCategory.HIGH_RISK
        assert "Anexo III" in report.risk_classification.annex_reference
        assert "Punto 5(a)" in report.risk_classification.annex_reference
        assert len(report.risk_classification.applicable_mandatory_requirements) >= 5

    def test_risk_classification_check_item(self, mock_covered_assessment: ClaimAssessment):
        report = generate_compliance_report(assessment=mock_covered_assessment)
        risk_check = next((c for c in report.checks if "Anexo III" in c.article_reference), None)
        assert risk_check is not None
        assert risk_check.status == ComplianceCheckStatus.COMPLIANT


class TestHumanInTheLoopOversight:
    """Tests for Art. 14 Human Oversight (Human-in-the-Loop)."""

    def test_human_in_the_loop_compliant(self, mock_covered_assessment: ClaimAssessment):
        report = generate_compliance_report(assessment=mock_covered_assessment)
        hitl = report.human_in_the_loop
        assert hitl.is_proposal is True
        assert hitl.human_validation_required is True
        assert hitl.status == ComplianceCheckStatus.COMPLIANT
        assert "gestor humano" in hitl.recommendation_summary.lower()

    def test_human_in_the_loop_partial_when_recommendation_lacks_human_terms(self):
        assessment = ClaimAssessment(
            claim_id="CLM-AUTONOMOUS",
            status=CoverageStatus.APPROVED,
            is_covered=True,
            coverage_summary="Aprobado automáticamente.",
            reasoning="Resolución directa.",
            recommendation="Indemnización automática emitida sin intervención.",
        )
        report = generate_compliance_report(assessment=assessment)
        assert report.human_in_the_loop.status == ComplianceCheckStatus.PARTIALLY_COMPLIANT


class TestTransparencyAndRecordKeeping:
    """Tests for Art. 12 (Logging) and Art. 13 (Transparency/Explicability)."""

    def test_transparency_with_full_traceability(self, mock_covered_assessment: ClaimAssessment):
        report = generate_compliance_report(assessment=mock_covered_assessment)
        trans = report.transparency_audit
        assert trans.has_traceability_logs is True
        assert trans.reasoning_provided is True
        assert len(trans.tools_executed) == 2
        assert trans.status == ComplianceCheckStatus.COMPLIANT
        assert trans.execution_time_seconds > 0.0
        assert trans.total_tokens_consumed == 500

    def test_transparency_partial_without_intermediate_steps(self):
        assessment = ClaimAssessment(
            claim_id="CLM-NO-STEPS",
            status=CoverageStatus.DENIED,
            is_covered=False,
            coverage_summary="Denegado.",
            reasoning="El desgaste de neumáticos no está cubierto por la póliza.",
            recommendation="Revisión por gestor de siniestros requerida.",
            intermediate_steps=[],
            metrics=ExecutionMetrics(),
        )
        report = generate_compliance_report(assessment=assessment)
        assert report.transparency_audit.status == ComplianceCheckStatus.PARTIALLY_COMPLIANT
        assert report.transparency_audit.has_traceability_logs is False


class TestDataGovernanceAndPrivacy:
    """Tests for Art. 10 Data Governance and GDPR Privacy by Design."""

    def test_privacy_audit_compliant_with_anonymized_claim(
        self, mock_covered_assessment: ClaimAssessment, mock_anonymized_claim: AnonymizedClaim
    ):
        report = generate_compliance_report(
            assessment=mock_covered_assessment,
            anonymized_claim=mock_anonymized_claim,
        )
        priv = report.privacy_audit
        assert priv.pii_masking_applied is True
        assert priv.detected_entities_count == 4
        assert priv.status == ComplianceCheckStatus.COMPLIANT

    def test_privacy_audit_partial_when_no_anonymization_evidence(
        self, mock_covered_assessment: ClaimAssessment
    ):
        report = generate_compliance_report(
            assessment=mock_covered_assessment,
            anonymized_claim=None,
        )
        priv = report.privacy_audit
        assert priv.pii_masking_applied is False
        assert priv.status == ComplianceCheckStatus.PARTIALLY_COMPLIANT


class TestAccuracyAndRobustness:
    """Tests for Art. 15 Accuracy, Robustness and Determinism."""

    def test_accuracy_check_valid_breakdown(self, mock_covered_assessment: ClaimAssessment):
        report = generate_compliance_report(assessment=mock_covered_assessment)
        art15_check = next((c for c in report.checks if "Art. 15" in c.article_reference), None)
        assert art15_check is not None
        assert art15_check.status == ComplianceCheckStatus.COMPLIANT


class TestCertificationAndScoring:
    """Tests for global certification score and status."""

    def test_full_compliant_report_is_certified(
        self, mock_covered_assessment: ClaimAssessment, mock_anonymized_claim: AnonymizedClaim
    ):
        report = generate_compliance_report(
            assessment=mock_covered_assessment,
            anonymized_claim=mock_anonymized_claim,
        )
        assert report.is_certified is True
        assert report.compliance_score == 100.0

    def test_partial_report_score_calculation(self, mock_covered_assessment: ClaimAssessment):
        # Without anonymized_claim, privacy check is PARTIALLY_COMPLIANT
        report = generate_compliance_report(
            assessment=mock_covered_assessment,
            anonymized_claim=None,
        )
        assert report.compliance_score >= 80.0
        assert report.is_certified is True

    def test_non_compliant_check_fails_certification(self, mock_covered_assessment: ClaimAssessment):
        report = generate_compliance_report(assessment=mock_covered_assessment)
        # Inject non-compliant check
        report.checks.append(
            ComplianceCheckItem(
                article_reference="Art. 5 Prohibited AI",
                name="Manipulative AI check",
                status=ComplianceCheckStatus.NON_COMPLIANT,
                description="Test non compliant",
                evidence="Failed safety check",
            )
        )
        # Trigger recalculation via model validator or manual test
        report_recomputed = EUAIActComplianceReport(
            claim_id=report.claim_id,
            risk_classification=report.risk_classification,
            human_in_the_loop=report.human_in_the_loop,
            transparency_audit=report.transparency_audit,
            privacy_audit=report.privacy_audit,
            checks=report.checks,
        )
        assert report_recomputed.is_certified is False


class TestFormattingAndExport:
    """Tests for Markdown formatting and JSON export."""

    def test_format_compliance_report_markdown(
        self, mock_covered_assessment: ClaimAssessment, mock_anonymized_claim: AnonymizedClaim
    ):
        report = generate_compliance_report(
            assessment=mock_covered_assessment,
            anonymized_claim=mock_anonymized_claim,
        )
        md = format_compliance_report_markdown(report)

        assert "# ⚖️ Ficha Técnica de Cumplimiento — EU AI Act" in md
        assert "CLM-TEST-001" in md
        assert "Alto Riesgo (Anexo III)" in md
        assert "Supervisión Humana Efectiva (Human-in-the-Loop - Art. 14)" in md
        assert "Transparencia, Trazabilidad y Explicabilidad (Art. 12 & Art. 13)" in md
        assert "Gobernanza de Datos y Privacidad (Art. 10 & RGPD)" in md
        assert "| Artículo / Marco | Control de Gobernanza | Estado | Evidencia Técnica Auditada |" in md
        assert "CERTIFICADO CONFORME" in md

    def test_export_compliance_report_dict(
        self, mock_covered_assessment: ClaimAssessment, mock_anonymized_claim: AnonymizedClaim
    ):
        report = generate_compliance_report(
            assessment=mock_covered_assessment,
            anonymized_claim=mock_anonymized_claim,
        )
        data = export_compliance_report_dict(report)

        assert isinstance(data, dict)
        assert data["claim_id"] == "CLM-TEST-001"
        assert data["risk_classification"]["category"] == RiskCategory.HIGH_RISK.value
        assert data["human_in_the_loop"]["is_proposal"] is True
        assert data["transparency_audit"]["has_traceability_logs"] is True
        assert data["privacy_audit"]["detected_entities_count"] == 4
        assert len(data["checks"]) >= 5


class TestEndToEndComplianceIntegration:
    """Tests for the end-to-end integration via evaluate_claim_with_compliance."""

    def test_evaluate_claim_with_compliance_from_claim_input(self):
        claim_in = ClaimInput(
            claim_id="CLM-E2E-001",
            raw_text="El asegurado Antonio López con DNI 77889900A y matrícula 9988-ZZZ sufrió rotura de luna delantera por granizo.",
        )
        anonymized = anonymize_claim(claim_in)
        assessment, report = evaluate_claim_with_compliance(
            claim=anonymized,
            force_deterministic=True,
        )

        assert isinstance(assessment, ClaimAssessment)
        assert isinstance(report, EUAIActComplianceReport)
        assert assessment.claim_id == "CLM-E2E-001"
        assert report.claim_id == "CLM-E2E-001"
        assert report.is_certified is True
        assert report.risk_classification.category == RiskCategory.HIGH_RISK
        assert report.privacy_audit.pii_masking_applied is True
        assert report.privacy_audit.detected_entities_count >= 2
        assert report.transparency_audit.has_traceability_logs is True
