"""E2E / Integration Test Execution Engine for GuardSeguro AI (US-09).

Executes end-to-end claim assessments across predefined demonstration cases
and validates agent behavior against expected ground truth:
1. Herramientas invocadas (Tools called).
2. Resolución / Dictamen de cobertura (Resolution status).
3. Total a indemnizar (Payout amount).
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.agent.claim_agent import evaluate_claim_with_compliance
from src.compliance.models import EUAIActComplianceReport
from src.core.config import Settings, get_settings
from src.core.models import AnonymizedClaim, ClaimAssessment, ClaimInput, CoverageStatus
from src.privacy.masker import anonymize_claim
from src.ui.sample_cases import SAMPLE_CASES, SampleCase

logger = logging.getLogger(__name__)


@dataclass
class TestCaseResult:
    """Result of evaluating a single sample claim test case against ground truth."""

    __test__ = False

    case: SampleCase
    claim_input: Optional[ClaimInput] = None
    anonymized_claim: Optional[AnonymizedClaim] = None
    assessment: Optional[ClaimAssessment] = None
    compliance_report: Optional[EUAIActComplianceReport] = None

    # Validation evaluation checks
    tools_passed: bool = False
    status_passed: bool = False
    payout_passed: bool = False
    passed: bool = False

    # Observed values
    actual_tools: List[str] = field(default_factory=list)
    actual_status: str = ""
    actual_payout: float = 0.0

    # Latency & Error tracking
    execution_time_seconds: float = 0.0
    error: Optional[str] = None

    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert result to a structured summary dictionary."""
        return {
            "case_id": self.case.case_id,
            "title": self.case.title,
            "category": self.case.category,
            "policy_type": self.case.policy_type,
            "passed": self.passed,
            "tools_passed": self.tools_passed,
            "status_passed": self.status_passed,
            "payout_passed": self.payout_passed,
            "expected_tools": self.case.expected_tools,
            "actual_tools": self.actual_tools,
            "expected_status": self.case.expected_status,
            "actual_status": self.actual_status,
            "expected_payout": self.case.expected_payout,
            "actual_payout": self.actual_payout,
            "execution_time_seconds": self.execution_time_seconds,
            "error": self.error,
        }


def normalize_status_str(status_val: Any) -> str:
    """Normalize status string or enum to unified lower-cased title format."""
    if isinstance(status_val, CoverageStatus):
        return status_val.value.strip().title()
    text = str(status_val).strip().replace("_", " ").title()
    if "Aprobad" in text:
        return "Aprobado"
    if "Denegad" in text:
        return "Denegado"
    if "Peritaje" in text or "Expert" in text:
        return "Requiere Peritaje"
    return text


def evaluate_single_test_case(
    case: SampleCase,
    force_deterministic: bool = True,
    settings: Optional[Settings] = None,
) -> TestCaseResult:
    """Execute end-to-end evaluation for one test case and check against ground truth.

    Args:
        case: The sample test case to evaluate.
        force_deterministic: Whether to force offline deterministic engine.
        settings: Application settings.

    Returns:
        TestCaseResult with PASS/FAIL evaluation.
    """
    settings = settings or get_settings()
    start_time = time.perf_counter()

    claim_input = ClaimInput(
        claim_id=case.case_id,
        policy_type=case.policy_type,
        raw_text=case.raw_text,
    )

    try:
        # 1. PII Anonymization
        anonymized_claim = anonymize_claim(claim_input)

        # 2. Agent Assessment + EU AI Act Audit
        assessment, compliance_report = evaluate_claim_with_compliance(
            claim=anonymized_claim,
            claim_id=case.case_id,
            policy_type=case.policy_type,
            force_deterministic=force_deterministic,
            settings=settings,
        )

        elapsed = round(time.perf_counter() - start_time, 3)

        # Extract actual values
        actual_tools = assessment.metrics.tools_called if assessment.metrics else []
        actual_status_normalized = normalize_status_str(assessment.status)
        expected_status_normalized = normalize_status_str(case.expected_status)
        actual_payout = round(float(assessment.net_payout), 2)

        # Criterion 1: Tools Check (Expected tools must be invoked)
        tools_passed = set(case.expected_tools).issubset(set(actual_tools))

        # Criterion 2: Resolution Status Check
        status_passed = actual_status_normalized == expected_status_normalized

        # Criterion 3: Payout Check (tolerance within 0.05 EUR)
        payout_passed = abs(actual_payout - float(case.expected_payout)) < 0.05

        # Overall PASS iff all three criteria pass
        overall_passed = tools_passed and status_passed and payout_passed

        return TestCaseResult(
            case=case,
            claim_input=claim_input,
            anonymized_claim=anonymized_claim,
            assessment=assessment,
            compliance_report=compliance_report,
            tools_passed=tools_passed,
            status_passed=status_passed,
            payout_passed=payout_passed,
            passed=overall_passed,
            actual_tools=actual_tools,
            actual_status=actual_status_normalized,
            actual_payout=actual_payout,
            execution_time_seconds=elapsed,
            error=None,
        )

    except Exception as exc:
        elapsed = round(time.perf_counter() - start_time, 3)
        logger.exception("Error running E2E test case %s: %s", case.case_id, exc)
        return TestCaseResult(
            case=case,
            claim_input=claim_input,
            tools_passed=False,
            status_passed=False,
            payout_passed=False,
            passed=False,
            execution_time_seconds=elapsed,
            error=str(exc),
        )


def run_all_e2e_suite(
    cases: Optional[List[SampleCase]] = None,
    force_deterministic: bool = True,
    settings: Optional[Settings] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> List[TestCaseResult]:
    """Execute all test cases in the suite and return results.

    Args:
        cases: Optional custom list of cases. Defaults to SAMPLE_CASES.
        force_deterministic: Whether to use deterministic engine.
        settings: Application settings.
        progress_callback: Optional callback receiving (completed_count, total_count, current_case_title).

    Returns:
        List of TestCaseResult objects.
    """
    cases = cases or SAMPLE_CASES
    results: List[TestCaseResult] = []
    total = len(cases)

    for i, case in enumerate(cases, start=1):
        if progress_callback:
            progress_callback(i - 1, total, f"Ejecutando {case.case_id}: {case.title}...")

        res = evaluate_single_test_case(
            case=case,
            force_deterministic=force_deterministic,
            settings=settings,
        )
        results.append(res)

        if progress_callback:
            progress_callback(i, total, f"Completado {case.case_id} ({'PASS' if res.passed else 'FAIL'})")

    return results
