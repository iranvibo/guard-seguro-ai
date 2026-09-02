"""Risk, dispute, and fraud indicator assessment tool for Allianz Spain.

Analyzes insurance claim declarations to identify contradictory statements,
third-party disputes, lack of conclusive police reports (atestados),
severe structural damages, speed infractions, and potential fraud indicators
that necessitate physical expert appraisal (Requiere Peritaje) or legal review.
"""

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    """Normalize text by lowercasing, removing accents and non-alphanumeric chars."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    only_ascii = "".join([c for c in nfkd if not unicodedata.combining(c)])
    clean = re.sub(r"[^\w\s]", " ", only_ascii.lower())
    return re.sub(r"\s+", " ", clean).strip()


DISPUTE_INDICATORS = [
    ("versiones contradictorias", "Versiones contradictorias entre los conductores implicados sobre la dinámica del siniestro."),
    ("version contradictoria", "Versión contradictoria sobre la responsabilidad del siniestro."),
    ("prioridad de paso", "Conflicto o discrepancia sobre la prioridad de paso y preferencia."),
    ("denuncia", "Denuncia formal presentada por alguna de las partes o terceros implicados."),
    ("denuncias", "Denuncias cruzadas presentadas por terceros implicados."),
    ("sin atestado", "Ausencia de atestado policial o parte amistoso de accidente (DAA) firmado."),
    ("no hay atestado", "Falta de atestado policial concluyente."),
    ("atestado no concluyente", "Atestado policial inconcluso o no determinante de la responsabilidad."),
    ("atestado policial no concluyente", "Atestado policial sin determinación concluyente de culpa."),
    ("discrepancia", "Discrepancia manifiesta en la descripción de los hechos."),
    ("sin acuerdo", "Ausencia de acuerdo amistoso entre las partes involucradas."),
]

SEVERITY_AND_FRAUD_INDICATORS = [
    ("exceso de velocidad", "Indicios reportados de posible exceso de velocidad o conducción antirreglamentaria."),
    ("velocidad excesiva", "Posible exceso de velocidad durante el incidente."),
    ("chasis", "Daños estructurales severos en el chasis que comprometen la seguridad y requieren bancada/inspección."),
    ("danos estructurales", "Daños estructurales severos que exigen peritaje presencial obligatorio."),
    ("siniestro total", "Indicios de posible siniestro total técnico o económico."),
    ("fraude", "Alerta de posible simulación o fraude que requiere intervención de la unidad antifraude."),
    ("incoherencia", "Incoherencia entre la dinámica relatada y la magnitud de los daños."),
    ("falta de mantenimiento", "Indicios de falta de mantenimiento o desgaste paulatino que exigen dictamen pericial o verificación de exclusión."),
    ("mantenimiento deficiente", "Posible falta de mantenimiento preventivo o correctivo."),
    ("corrosion natural", "Corrosión natural o deterioro progresivo de elementos."),
    ("mas de un ano", "Siniestro reportado con dilación superior a un año o evolución crónica continuada."),
    ("mas de 1 ano", "Siniestro prolongado durante más de un año sin notificación inmediata."),
    ("filtraciones continuadas", "Filtraciones y humedades continuadas en el tiempo que requieren verificar origen y agravación del daño."),
    ("cubierta", "Afectación de cubierta o elementos de estanqueidad exterior del inmueble que requieren peritaje."),
    ("tejado", "Daños en tejado o cubierta del inmueble que requieren peritaje de estanqueidad."),
]


@dataclass
class ClaimRiskEvaluation:
    """Structured representation of claim risk and dispute analysis."""

    requires_expert_appraisal: bool
    risk_level: str  # "Bajo", "Medio", "Alto"
    alerts: List[str]
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requiere_peritaje": self.requires_expert_appraisal,
            "nivel_riesgo": self.risk_level,
            "alertas_detectadas": self.alerts,
            "recomendacion_accion": self.recommendation,
            "requires_expert_appraisal": self.requires_expert_appraisal,
            "risk_level": self.risk_level,
            "alerts": self.alerts,
            "recommendation": self.recommendation,
        }


def evaluate_claim_risk(claim_text: str) -> ClaimRiskEvaluation:
    """Evaluate dispute and risk indicators in claim declaration text.

    Args:
        claim_text: Raw or anonymized text of the claim declaration.

    Returns:
        ClaimRiskEvaluation object with risk assessment and actionable recommendations.
    """
    norm = _normalize_text(claim_text)
    alerts: List[str] = []

    # Check dispute & liability conflict indicators
    for kw, description in DISPUTE_INDICATORS:
        norm_kw = _normalize_text(kw)
        if norm_kw in norm and description not in alerts:
            alerts.append(description)

    # Check severity, speed, structural damage and fraud indicators
    for kw, description in SEVERITY_AND_FRAUD_INDICATORS:
        norm_kw = _normalize_text(kw)
        if norm_kw in norm and description not in alerts:
            alerts.append(description)

    if not alerts:
        return ClaimRiskEvaluation(
            requires_expert_appraisal=False,
            risk_level="Bajo",
            alerts=[],
            recommendation="Siniestro estándar sin controversias ni alertas de riesgo. Puede continuar con tramitación ordinaria.",
        )

    # Determine risk level
    is_high_risk = len(alerts) >= 2 or any(
        "contradictorias" in a.lower()
        or "denuncia" in a.lower()
        or "estructurales" in a.lower()
        or "chasis" in a.lower()
        or "fraude" in a.lower()
        for a in alerts
    )

    risk_level = "Alto" if is_high_risk else "Medio"
    recommendation = (
        "Requiere Peritaje presencial y/o investigación jurídica obligatoria. "
        "NO proceder con el pago automático directo de la indemnización hasta que el perito "
        "o tramitador humano esclarezca la responsabilidad y verifique la cuantía de los daños estructurales."
    )

    return ClaimRiskEvaluation(
        requires_expert_appraisal=True,
        risk_level=risk_level,
        alerts=alerts,
        recommendation=recommendation,
    )


@tool
def assess_claim_risk_and_dispute(claim_text: str) -> str:
    """Evalúa indicadores de riesgo, controversia de culpabilidad, denuncias de terceros, atestados y daños estructurales en el siniestro.

    Analiza si existen versiones contradictorias, ausencia de atestado concluyente,
    denuncias de terceros, posibles excesos de velocidad o daños estructurales en chasis
    que exijan suspender la liquidación directa y clasificar la resolución como 'Requiere Peritaje'.

    Args:
        claim_text: Texto íntegro o descripción del siniestro declarado por el asegurado.

    Returns:
        JSON estructurado con:
        - requiere_peritaje (bool): True si el siniestro debe derivarse obligatoriamente a peritaje presencial / asesoría jurídica.
        - nivel_riesgo (str): 'Bajo', 'Medio' o 'Alto'.
        - alertas_detectadas (List[str]): Lista de motivos de alerta identificados.
        - recomendacion_accion (str): Pautas obligatorias para el tramitador (Human-in-the-Loop).
    """
    evaluation = evaluate_claim_risk(claim_text)
    return json.dumps(evaluation.to_dict(), ensure_ascii=False, indent=2)
