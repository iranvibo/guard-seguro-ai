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
    """Structure representing a predefined demonstration claim and its expected ground truth."""

    case_id: str
    title: str
    short_description: str
    category: str
    icon: str
    policy_type: str
    raw_text: str
    expected_status: str
    tags: List[str]
    expected_tools: List[str]
    expected_payout: float
    expected_is_covered: bool


SAMPLE_CASES: List[SampleCase] = [
    SampleCase(
        case_id="CASO-01",
        title="Tormenta con cobertura (Auto - Granizo y Lunas)",
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
        expected_status="Aprobado",
        tags=["Auto", "Granizo", "Rotura de Lunas", "Chapa", "Sin Franquicia"],
        expected_tools=["check_policy_coverage", "assess_claim_risk_and_dispute", "calculate_repair_estimate"],
        expected_payout=1020.0,
        expected_is_covered=True,
    ),
    SampleCase(
        case_id="CASO-02",
        title="Daño no cubierto (Auto - Desgaste y Avería Mecánica)",
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
        expected_status="Denegado",
        tags=["Auto", "Desgaste", "Avería Mecánica", "Exclusión General", "Sin Cobertura"],
        expected_tools=["check_policy_coverage"],
        expected_payout=0.0,
        expected_is_covered=False,
    ),
    SampleCase(
        case_id="CASO-03",
        title="Caso complejo con terceros (Auto - Colisión Múltiple)",
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
        expected_status="Requiere Peritaje",
        tags=["Auto", "Colisión Múltiple", "Terceros", "Daño Estructural", "Peritaje Técnico"],
        expected_tools=["check_policy_coverage", "assess_claim_risk_and_dispute"],
        expected_payout=0.0,
        expected_is_covered=True,
    ),
    SampleCase(
        case_id="CASO-04",
        title="Tormenta con cobertura (Hogar - Cristales y Temporal)",
        short_description="Rotura de ventanal Climalit y claraboya por fuerte tormenta de pedrisco en vivienda.",
        category="Cobertura Favorable",
        icon="⛈️",
        policy_type="Hogar",
        raw_text=(
            "La asegurada María Dolores Ruiz Santos con DNI 33445566T y teléfono 622334455 declara siniestro "
            "ocurrido en su vivienda unifamiliar en Calle Rosales 12, Pozuelo de Alarcón (Madrid). A causa de la fuerte tormenta "
            "de pedrisco y viento extremo registrada oficialmente por AEMET, se produjo la rotura completa del cristal "
            "climalit del ventanal del salón y la fractura de la claraboya del ático, requiriendo reposición urgente "
            "de cristalería de la vivienda."
        ),
        expected_status="Aprobado",
        tags=["Hogar", "Fenómenos Atmosféricos", "Cristalería Hogar", "Sin Franquicia"],
        expected_tools=["check_policy_coverage", "assess_claim_risk_and_dispute", "calculate_repair_estimate"],
        expected_payout=290.0,
        expected_is_covered=True,
    ),
    SampleCase(
        case_id="CASO-05",
        title="Daños por agua con cobertura (Hogar - Rotura Tubería)",
        short_description="Fuga de agua en tubería empotrada de cocina con afectación al vecino inferior.",
        category="Cobertura Favorable",
        icon="💧",
        policy_type="Hogar",
        raw_text=(
            "El tomador Javier Navarro Vidal con DNI 50876543M y teléfono 678123456 notifica siniestro en su piso "
            "de Calle Gran Vía 88, Valencia. Ha detectado una fuga accidental por rotura en la conducción empotrada "
            "de agua sanitaria bajo el fregadero de la cocina, causando inundación en el suelo y filtración con daños "
            "por humedad en el techo de la vivienda del vecino inferior. Solicita fontanería y reparación urgente."
        ),
        expected_status="Aprobado",
        tags=["Hogar", "Daños por Agua", "Fontanería", "Responsabilidad Civil"],
        expected_tools=["check_policy_coverage", "assess_claim_risk_and_dispute", "calculate_repair_estimate"],
        expected_payout=400.0,
        expected_is_covered=True,
    ),
    SampleCase(
        case_id="CASO-06",
        title="Daño no cubierto (Hogar - Falta de Mantenimiento)",
        short_description="Humedades crónicas en tejado y goteras debidas a corrosión y falta de mantenimiento.",
        category="Exclusión de Póliza",
        icon="🚫",
        policy_type="Hogar",
        raw_text=(
            "El asegurado Pedro Sánchez Alarcón con DNI 09876543K y correo p.sanchez@example.com solicita la reparación "
            "del tejado de su vivienda unifamiliar en Calle Encinas 5 de Toledo. Informa de goteras y filtraciones continuadas "
            "desde hace más de un año debido a la corrosión natural de los canalones atascados y el desgaste por falta de "
            "mantenimiento periódico prescrito en la cubierta del inmueble."
        ),
        expected_status="Denegado",
        tags=["Hogar", "Falta de Mantenimiento", "Deterioro Paulatino", "Sin Cobertura"],
        expected_tools=["check_policy_coverage"],
        expected_payout=0.0,
        expected_is_covered=False,
    ),
]


def get_sample_case_by_id(case_id: str) -> SampleCase:
    """Retrieve a sample test case by its ID."""
    for case in SAMPLE_CASES:
        if case.case_id == case_id:
            return case
    return SAMPLE_CASES[0]
