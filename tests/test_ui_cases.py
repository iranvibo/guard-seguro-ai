"""Unit and integration tests for UI components and sample test cases (US-09)."""

import pytest

from src.agent.claim_agent import evaluate_claim_with_compliance
from src.compliance.models import ComplianceCheckStatus, EUAIActComplianceReport
from src.core.models import ClaimAssessment, ClaimInput, CoverageStatus
from src.privacy.masker import anonymize_claim
from src.ui.sample_cases import SAMPLE_CASES, SampleCase, get_sample_case_by_id


class TestUISampleCases:
    """Validate sample cases integrity and expectations."""

    def test_sample_cases_count_and_structure(self):
        """DoD: Selector contains 3 predefined test cases."""
        assert len(SAMPLE_CASES) >= 3
        expected_ids = {"CASO-01", "CASO-02", "CASO-03"}
        actual_ids = {case.case_id for case in SAMPLE_CASES}
        assert expected_ids.issubset(actual_ids)

        for case in SAMPLE_CASES:
            assert isinstance(case, SampleCase)
            assert len(case.case_id) > 0
            assert len(case.title) > 0
            assert len(case.short_description) > 0
            assert len(case.raw_text) > 20
            assert case.policy_type in ["Auto", "Hogar"]
            assert len(case.tags) > 0

    def test_get_sample_case_by_id(self):
        """Ensure lookup by ID works correctly."""
        case_1 = get_sample_case_by_id("CASO-01")
        assert case_1.case_id == "CASO-01"
        assert "Tormenta" in case_1.title

        case_2 = get_sample_case_by_id("CASO-02")
        assert case_2.case_id == "CASO-02"
        assert "Desgaste" in case_2.title

        fallback = get_sample_case_by_id("NON-EXISTENT")
        assert fallback == SAMPLE_CASES[0]

    def test_sample_cases_pii_masking(self):
        """Ensure all sample cases contain PII and are properly masked by US-03 engine."""
        for case in SAMPLE_CASES:
            claim_input = ClaimInput(
                claim_id=case.case_id,
                policy_type=case.policy_type,
                raw_text=case.raw_text,
            )
            anonymized = anonymize_claim(claim_input)
            assert anonymized.detected_entities_count > 0
            assert len(anonymized.pii_mapping) > 0
            assert anonymized.anonymized_text != case.raw_text

    def test_sample_case_1_covered_flow(self):
        """Ensure CASO-01 (Tormenta) yields approved resolution with deductible."""
        case = get_sample_case_by_id("CASO-01")
        claim_input = ClaimInput(
            claim_id=case.case_id,
            policy_type=case.policy_type,
            raw_text=case.raw_text,
        )
        anonymized = anonymize_claim(claim_input)

        assessment, compliance_report = evaluate_claim_with_compliance(
            claim=anonymized,
            force_deterministic=True,
        )

        assert isinstance(assessment, ClaimAssessment)
        assert assessment.status == CoverageStatus.APPROVED
        assert assessment.is_covered is True
        assert assessment.cost_breakdown is not None
        assert assessment.cost_breakdown.gross_total > 0
        assert assessment.cost_breakdown.net_total > 0
        assert isinstance(compliance_report, EUAIActComplianceReport)
        assert len(compliance_report.checks) >= 5

    def test_sample_case_2_denied_flow(self):
        """Ensure CASO-02 (Desgaste) yields denied resolution."""
        case = get_sample_case_by_id("CASO-02")
        claim_input = ClaimInput(
            claim_id=case.case_id,
            policy_type=case.policy_type,
            raw_text=case.raw_text,
        )
        anonymized = anonymize_claim(claim_input)

        assessment, compliance_report = evaluate_claim_with_compliance(
            claim=anonymized,
            force_deterministic=True,
        )

        assert isinstance(assessment, ClaimAssessment)
        assert assessment.status == CoverageStatus.DENIED
        assert assessment.is_covered is False
        assert assessment.net_payout == 0.0
        assert isinstance(compliance_report, EUAIActComplianceReport)

    def test_sample_case_3_complex_flow(self):
        """Ensure CASO-03 (Colisión Compleja / Terceros) yields resolution requiring expert or assessment."""
        case = get_sample_case_by_id("CASO-03")
        claim_input = ClaimInput(
            claim_id=case.case_id,
            policy_type=case.policy_type,
            raw_text=case.raw_text,
        )
        anonymized = anonymize_claim(claim_input)

        assessment, compliance_report = evaluate_claim_with_compliance(
            claim=anonymized,
            policy_type=case.policy_type,
            force_deterministic=True,
        )

        assert isinstance(assessment, ClaimAssessment)
        assert assessment.status in [CoverageStatus.APPROVED, CoverageStatus.REQUIRES_EXPERT]
        assert isinstance(compliance_report, EUAIActComplianceReport)

    def test_sample_case_4_hogar_storm_flow(self):
        """Ensure CASO-04 (Hogar - Tormenta y Cristales) yields approved resolution."""
        case = get_sample_case_by_id("CASO-04")
        claim_input = ClaimInput(
            claim_id=case.case_id,
            policy_type=case.policy_type,
            raw_text=case.raw_text,
        )
        anonymized = anonymize_claim(claim_input)

        assessment, compliance_report = evaluate_claim_with_compliance(
            claim=anonymized,
            policy_type=case.policy_type,
            force_deterministic=True,
        )

        assert isinstance(assessment, ClaimAssessment)
        assert assessment.status == CoverageStatus.APPROVED
        assert assessment.is_covered is True
        assert assessment.cost_breakdown is not None
        assert assessment.cost_breakdown.net_total > 0
        assert isinstance(compliance_report, EUAIActComplianceReport)

    def test_sample_case_5_hogar_water_damage_flow(self):
        """Ensure CASO-05 (Hogar - Daños por Agua) yields approved resolution."""
        case = get_sample_case_by_id("CASO-05")
        claim_input = ClaimInput(
            claim_id=case.case_id,
            policy_type=case.policy_type,
            raw_text=case.raw_text,
        )
        anonymized = anonymize_claim(claim_input)

        assessment, compliance_report = evaluate_claim_with_compliance(
            claim=anonymized,
            policy_type=case.policy_type,
            force_deterministic=True,
        )

        assert isinstance(assessment, ClaimAssessment)
        assert assessment.status == CoverageStatus.APPROVED
        assert assessment.is_covered is True
        assert assessment.cost_breakdown is not None
        assert assessment.cost_breakdown.net_total > 0
        assert isinstance(compliance_report, EUAIActComplianceReport)

    def test_sample_case_6_hogar_wear_tear_exclusion(self):
        """Ensure CASO-06 (Hogar - Desgaste y Falta de Mantenimiento) yields denied resolution."""
        case = get_sample_case_by_id("CASO-06")
        claim_input = ClaimInput(
            claim_id=case.case_id,
            policy_type=case.policy_type,
            raw_text=case.raw_text,
        )
        anonymized = anonymize_claim(claim_input)

        assessment, compliance_report = evaluate_claim_with_compliance(
            claim=anonymized,
            policy_type=case.policy_type,
            force_deterministic=True,
        )

        assert isinstance(assessment, ClaimAssessment)
        assert assessment.status == CoverageStatus.DENIED
        assert assessment.is_covered is False
        assert assessment.net_payout == 0.0
        assert isinstance(compliance_report, EUAIActComplianceReport)
