"""Unit tests for GuardSeguro AI core domain models (US-02)."""

from datetime import datetime
import pytest
from pydantic import ValidationError

from src.core.models import (
    AnonymizedClaim,
    ClaimAssessment,
    ClaimInput,
    CostBreakdown,
    CoverageCheckResult,
    CoverageStatus,
    DamageSeverity,
)


class TestClaimInput:
    """Tests for ClaimInput model."""

    def test_claim_input_creation_defaults(self):
        claim = ClaimInput(raw_text="El asegurado Juan Pérez reporta rotura de parabrisas.")
        assert claim.claim_id.startswith("CLM-")
        assert claim.raw_text == "El asegurado Juan Pérez reporta rotura de parabrisas."
        assert isinstance(claim.incident_date, datetime)
        assert claim.policy_type == "Auto"
        assert claim.metadata == {}

    def test_claim_input_custom_values(self):
        custom_date = datetime(2026, 8, 15, 10, 30)
        claim = ClaimInput(
            claim_id="CLM-TEST-001",
            raw_text="Caída de granizo sobre chapa.",
            incident_date=custom_date,
            policy_id="POL-998877",
            policy_type="Hogar",
            metadata={"source": "call_center"},
        )
        assert claim.claim_id == "CLM-TEST-001"
        assert claim.policy_id == "POL-998877"
        assert claim.policy_type == "Hogar"
        assert claim.incident_date == custom_date
        assert claim.metadata["source"] == "call_center"

    def test_claim_input_empty_text_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ClaimInput(raw_text="   ")

    def test_claim_input_short_text_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ClaimInput(raw_text="Hi")


class TestAnonymizedClaim:
    """Tests for AnonymizedClaim model."""

    def test_anonymized_claim_creation(self):
        anon_claim = AnonymizedClaim(
            claim_id="CLM-12345",
            original_text="Juan Pérez con DNI 12345678Z conducía matrícula 1234-BBB",
            anonymized_text="[PERSONA_1] con DNI [DNI_1] conducía matrícula [MATRICULA_1]",
            pii_mapping={
                "[PERSONA_1]": "Juan Pérez",
                "[DNI_1]": "12345678Z",
                "[MATRICULA_1]": "1234-BBB",
            },
        )
        assert anon_claim.claim_id == "CLM-12345"
        assert anon_claim.detected_entities_count == 3
        assert len(anon_claim.pii_mapping) == 3
        assert anon_claim.pii_mapping["[PERSONA_1]"] == "Juan Pérez"
        assert isinstance(anon_claim.created_at, datetime)


class TestCoverageCheckResult:
    """Tests for CoverageCheckResult model."""

    def test_coverage_check_result(self):
        result = CoverageCheckResult(
            is_covered=True,
            coverage_type="Rotura de lunas",
            conditions="Cobertura 100% en talleres concertados sin penalización de bonus.",
            standard_deductible=0.0,
        )
        assert result.is_covered is True
        assert result.coverage_type == "Rotura de lunas"
        assert result.standard_deductible == 0.0


class TestCostBreakdown:
    """Tests for CostBreakdown model."""

    def test_cost_breakdown_auto_calculation(self):
        breakdown = CostBreakdown(
            materials=350.0,
            labor=150.0,
            deductible=100.0,
        )
        assert breakdown.gross_total == 500.0
        assert breakdown.deductible == 100.0
        assert breakdown.net_total == 400.0

    def test_cost_breakdown_net_total_never_negative(self):
        breakdown = CostBreakdown(
            materials=50.0,
            labor=30.0,
            deductible=150.0,
        )
        assert breakdown.gross_total == 80.0
        assert breakdown.deductible == 150.0
        assert breakdown.net_total == 0.0

    def test_cost_breakdown_negative_values_raise_error(self):
        with pytest.raises(ValidationError):
            CostBreakdown(materials=-10.0, labor=50.0)


class TestClaimAssessment:
    """Tests for ClaimAssessment model."""

    def test_claim_assessment_approved(self):
        breakdown = CostBreakdown(materials=400.0, labor=200.0, deductible=150.0)
        assessment = ClaimAssessment(
            claim_id="CLM-001",
            status=CoverageStatus.APPROVED,
            is_covered=True,
            coverage_summary="Daños por granizo con cobertura completa.",
            cost_breakdown=breakdown,
            reasoning="El siniestro cumple las condiciones de póliza a todo riesgo.",
            recommendation="Emitir orden de reparación al taller seleccionado.",
            intermediate_steps=[
                {"tool": "check_policy_coverage", "output": {"cubierto": True}},
                {"tool": "calculate_repair_estimate", "output": {"total": 600.0}},
            ],
        )
        assert assessment.status == CoverageStatus.APPROVED
        assert assessment.is_covered is True
        assert assessment.deductible == 150.0
        assert assessment.net_payout == 450.0
        assert len(assessment.intermediate_steps) == 2

    def test_claim_assessment_denied(self):
        assessment = ClaimAssessment(
            claim_id="CLM-002",
            status=CoverageStatus.DENIED,
            is_covered=False,
            coverage_summary="Desgaste natural de neumáticos sin cobertura.",
            cost_breakdown=None,
            reasoning="La póliza excluye expresamente el desgaste derivado del uso habitual.",
            recommendation="Notificar resolución desestimatoria al asegurado.",
        )
        assert assessment.status == CoverageStatus.DENIED
        assert assessment.is_covered is False
        assert assessment.net_payout == 0.0
        assert assessment.deductible == 0.0

    def test_claim_assessment_requires_expert(self):
        assessment = ClaimAssessment(
            claim_id="CLM-003",
            status=CoverageStatus.REQUIRES_EXPERT,
            is_covered=True,
            coverage_summary="Daños estructurales graves en chasis y motor.",
            cost_breakdown=CostBreakdown(materials=2500.0, labor=1800.0, deductible=300.0),
            reasoning="Importe superior al umbral de aprobación automática (3.000€).",
            recommendation="Asignar perito presencial para valoración in situ.",
        )
        assert assessment.status == CoverageStatus.REQUIRES_EXPERT
        assert assessment.net_payout == 4000.0

    def test_json_serialization_roundtrip(self):
        assessment = ClaimAssessment(
            claim_id="CLM-004",
            status=CoverageStatus.APPROVED,
            is_covered=True,
            coverage_summary="Rotura de luna delantera.",
            cost_breakdown=CostBreakdown(materials=220.0, labor=80.0, deductible=0.0),
            reasoning="Cobertura de lunas sin franquicia.",
        )
        json_str = assessment.model_dump_json()
        restored = ClaimAssessment.model_validate_json(json_str)
        assert restored.claim_id == assessment.claim_id
        assert restored.status == CoverageStatus.APPROVED
        assert restored.net_payout == 300.0
