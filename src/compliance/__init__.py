"""Compliance module: EU AI Act audit reports and governance metrics (US-08).

Provides tools for high-risk classification, human-in-the-loop oversight validation,
transparency accreditation, and automated technical audit sheets for GuardSeguro Seguros.
"""

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

__all__ = [
    "RiskCategory",
    "ComplianceCheckStatus",
    "ComplianceCheckItem",
    "RiskClassification",
    "HumanInTheLoopAudit",
    "TransparencyAudit",
    "DataPrivacyAudit",
    "EUAIActComplianceReport",
    "EUAIActAuditor",
    "generate_compliance_report",
    "format_compliance_report_markdown",
    "export_compliance_report_dict",
]
