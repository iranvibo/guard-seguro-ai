"""Unit and integration tests for the E2E Test Suite and evaluation runner."""

import pytest

from src.core.config import get_settings
from src.ui.e2e_runner import (
    TestCaseResult,
    evaluate_single_test_case,
    normalize_status_str,
    run_all_e2e_suite,
)
from src.ui.sample_cases import SAMPLE_CASES, get_sample_case_by_id


class TestE2ERunner:
    """Test suite for the interactive E2E runner validating agent ground truth."""

    def test_normalize_status_str(self):
        """Ensure status strings are properly normalized across formats."""
        assert normalize_status_str("APROBADO") == "Aprobado"
        assert normalize_status_str("Aprobado") == "Aprobado"
        assert normalize_status_str("DENEGADO") == "Denegado"
        assert normalize_status_str("Denegado") == "Denegado"
        assert normalize_status_str("REQUIERE_PERITAJE") == "Requiere Peritaje"
        assert normalize_status_str("Requiere Peritaje") == "Requiere Peritaje"

    def test_evaluate_single_case_1_tormenta_auto(self):
        """CASO-01: Approved storm claim with tools and calculation."""
        case = get_sample_case_by_id("CASO-01")
        settings = get_settings()

        result = evaluate_single_test_case(case, force_deterministic=True, settings=settings)

        assert isinstance(result, TestCaseResult)
        assert result.passed is True
        assert result.tools_passed is True
        assert result.status_passed is True
        assert result.payout_passed is True
        assert result.actual_status == "Aprobado"
        assert result.actual_payout == 1020.0
        assert "check_policy_coverage" in result.actual_tools
        assert "calculate_repair_estimate" in result.actual_tools
        assert result.execution_time_seconds > 0

    def test_evaluate_single_case_2_desgaste_auto(self):
        """CASO-02: Denied wear & tear claim."""
        case = get_sample_case_by_id("CASO-02")
        settings = get_settings()

        result = evaluate_single_test_case(case, force_deterministic=True, settings=settings)

        assert result.passed is True
        assert result.tools_passed is True
        assert result.status_passed is True
        assert result.payout_passed is True
        assert result.actual_status == "Denegado"
        assert result.actual_payout == 0.0
        assert "check_policy_coverage" in result.actual_tools

    def test_evaluate_single_case_3_colision_peritaje(self):
        """CASO-03: Complex collision claim requiring expert inspection."""
        case = get_sample_case_by_id("CASO-03")
        settings = get_settings()

        result = evaluate_single_test_case(case, force_deterministic=True, settings=settings)

        assert result.passed is True
        assert result.tools_passed is True
        assert result.status_passed is True
        assert result.payout_passed is True
        assert result.actual_status == "Requiere Peritaje"
        assert result.actual_payout == 0.0
        assert "check_policy_coverage" in result.actual_tools
        assert "assess_claim_risk_and_dispute" in result.actual_tools
        assert "calculate_repair_estimate" not in result.actual_tools

    def test_run_all_e2e_suite_all_pass(self):
        """Run all 6 predefined demo cases through the E2E runner and assert 100% pass rate."""
        settings = get_settings()
        progress_events = []

        def callback(current, total, msg):
            progress_events.append((current, total, msg))

        results = run_all_e2e_suite(
            cases=SAMPLE_CASES,
            force_deterministic=True,
            settings=settings,
            progress_callback=callback,
        )

        assert len(results) == len(SAMPLE_CASES)
        assert len(progress_events) > 0

        for r in results:
            assert r.passed is True, f"Failed case {r.case.case_id}: tools={r.tools_passed}, status={r.status_passed}, payout={r.payout_passed}, error={r.error}"
            assert r.assessment is not None
            assert r.compliance_report is not None
            summary = r.to_summary_dict()
            assert summary["passed"] is True
            assert summary["case_id"] == r.case.case_id
