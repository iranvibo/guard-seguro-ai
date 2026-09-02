"""Predefined realistic test cases for GuardSeguro AI Streamlit demonstration (US-09).

Provides representative insurance claim scenarios covering:
1. Covered storm/weather damage with deductible and calculation.
2. Explicitly excluded damage (mechanical failure/wear & tear).
3. Complex multi-party accident requiring expert inspection.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class SampleCase:
    """Structure representing a predefined demonstration claim."""

    case_id: str
    title: str
    short_description: str
    category: str
    icon: str
    policy_type: str
    raw_text: str
    expected_status: str
    tags: List[str]


SAMPLE_CASES: List[SampleCase] = [
    SampleCase(
        case_id="CASO-01",
        title="Tormenta con cobertura (Granizo y Lunas)",
        short_description="Rotura de luna delantera y abolladuras en chapa por fuerte pedrisco.",
        category="Cobertura Favorable",
        icon="⛈️",
        policy_type="Auto",
        raw_text=(
            "El asegurado Carlos Martínez Gómez con DNI 45871236K y teléfono 612345678 declara siniestro "
            "ocurrido el 28 de agosto en Calle Mayor 45 de Madrid. Su vehículo con matrícula 5678-LMN "
            "sufrió el impacto de una fuerte tormenta de granizo, provocando la rotura total de la luna delantera "
            "y abolladuras moderadas en la chapa del capó. Solicita indemnización en su cuenta bancaria "
            "ES9121000418450200051332 o reparación en taller concertado de Allianz."
        ),
        expected_status="APROBADO",
        tags=["Granizo", "Rotura de Lunas", "Chapa", "Con Franquicia"],
    ),
    SampleCase(
        case_id="CASO-02",
        title="Daño no cubierto (Desgaste y Avería Mecánica)",
        short_description="Fallo de embrague y deterioro por uso ordinario del vehículo.",
        category="Exclusión de Póliza",
        icon="🚫",
        policy_type="Auto",
        raw_text=(
            "La clienta Laura Fernández Blanco, con DNI 78945612B y correo l.fernandez@example.com, "
            "residente en Avenida Diagonal 120 de Barcelona (teléfono 934567890), notifica que su coche "
            "matrícula 9012-KZX se detuvo en autopista debido al desgaste continuado del disco de embrague "
            "y falta de mantenimiento mecánico periódico. Reclama el reembolso íntegro de la factura del taller."
        ),
        expected_status="DENEGADO",
        tags=["Desgaste", "Avería Mecánica", "Exclusión General", "Sin Cobertura"],
    ),
    SampleCase(
        case_id="CASO-03",
        title="Caso complejo con terceros (Colisión Múltiple)",
        short_description="Colisión con daños estructurales severos y partes contradictorios.",
        category="Derivación a Peritaje",
        icon="🔍",
        policy_type="Auto",
        raw_text=(
            "El conductor Antonio Romero Sanz (DNI 12345678Z, móvil 654987321) con domicilio en "
            "Paseo de la Castellana 200, Madrid, conducía el vehículo 1234-BBB cuando se vio involucrado "
            "en una colisión múltiple con otros dos vehículos de terceros. Existen versiones contradictorias "
            "sobre la prioridad de paso, posible exceso de velocidad y daños estructurales severos en el chasis "
            "y motor. Los terceros implicados han presentado denuncia y no hay atestado policial concluyente."
        ),
        expected_status="REQUIERE_PERITAJE",
        tags=["Colisión Múltiple", "Terceros", "Daño Estructural", "Peritaje Técnico"],
    ),
]


def get_sample_case_by_id(case_id: str) -> SampleCase:
    """Retrieve a sample test case by its ID."""
    for case in SAMPLE_CASES:
        if case.case_id == case_id:
            return case
    return SAMPLE_CASES[0]
