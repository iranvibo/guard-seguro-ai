"""Unit tests for PII Detection, Masking and Unmasking module (US-03).

Verifies compliance with Responsible AI, GDPR, and Spanish insurance claim patterns.
"""

from src.core.models import ClaimInput
from src.privacy.masker import PIIMasker, anonymize_claim, mask_pii, unmask_pii


class TestPIIDetectionAndMasking:
    """Test individual entity recognition and tokenization."""

    def test_mask_dni_formats(self) -> None:
        text1 = "El tomador con DNI 12345678Z tuvo un percance."
        text2 = "Documento de identidad: 12.345.678-A del asegurado."
        text3 = "NIE presentado: X1234567A en comisaría."

        masked1, map1 = mask_pii(text1)
        assert "[DNI_1]" in masked1
        assert "12345678Z" not in masked1
        assert map1["[DNI_1]"] == "12345678Z"

        masked2, map2 = mask_pii(text2)
        assert "[DNI_1]" in masked2
        assert "12.345.678-A" not in masked2
        assert map2["[DNI_1]"] == "12.345.678-A"

        masked3, map3 = mask_pii(text3)
        assert "[DNI_1]" in masked3
        assert "X1234567A" not in masked3
        assert map3["[DNI_1]"] == "X1234567A"

    def test_mask_license_plates(self) -> None:
        # Modern post-2000 plate
        text_modern = "Vehículo asegurado con matrícula 4567-KLM colisionó."
        masked_mod, map_mod = mask_pii(text_modern)
        assert "[MATRICULA_1]" in masked_mod
        assert "4567-KLM" not in masked_mod
        assert map_mod["[MATRICULA_1]"] == "4567-KLM"

        # Classic provincial plate
        text_prov = "Coche antiguo matrícula M-1234-AB en garaje."
        masked_prov, map_prov = mask_pii(text_prov)
        assert "[MATRICULA_1]" in masked_prov
        assert "M-1234-AB" not in masked_prov
        assert map_prov["[MATRICULA_1]"] == "M-1234-AB"

    def test_mask_spanish_phones(self) -> None:
        text = "Contactar al móvil 612 345 678 o al fijo +34 91 123 45 67 de urgencia."
        masked, mapping = mask_pii(text)
        assert "[TELEFONO_1]" in masked
        assert "[TELEFONO_2]" in masked
        assert "612 345 678" not in masked
        assert "+34 91 123 45 67" not in masked
        assert len(mapping) == 2

    def test_mask_emails(self) -> None:
        text = "Enviar informe a siniestros.cliente@gmail.com inmediatamente."
        masked, mapping = mask_pii(text)
        assert "[EMAIL_1]" in masked
        assert "siniestros.cliente@gmail.com" not in masked
        assert mapping["[EMAIL_1]"] == "siniestros.cliente@gmail.com"

    def test_mask_iban(self) -> None:
        text = "Transferir indemnización a cuenta ES91 2100 0418 4502 0005 1332."
        masked, mapping = mask_pii(text)
        assert "[IBAN_1]" in masked
        assert "ES91 2100 0418 4502 0005 1332" not in masked
        assert mapping["[IBAN_1]"] == "ES91 2100 0418 4502 0005 1332"

    def test_mask_person_names(self) -> None:
        text = "El cliente Juan Pérez y la conductora María Rodríguez López informan del parte."
        masked, mapping = mask_pii(text)
        assert "[PERSONA_1]" in masked
        assert "[PERSONA_2]" in masked
        assert "Juan Pérez" not in masked
        assert "María Rodríguez López" not in masked
        assert mapping["[PERSONA_1]"] == "Juan Pérez"
        assert mapping["[PERSONA_2]"] == "María Rodríguez López"

    def test_mask_addresses(self) -> None:
        text = "El siniestro ocurrió frente a Calle Alcalá 45, Madrid."
        masked, mapping = mask_pii(text)
        assert "[DIRECCION_1]" in masked
        assert "Calle Alcalá 45, Madrid" not in masked
        assert mapping["[DIRECCION_1]"] == "Calle Alcalá 45, Madrid"

    def test_same_entity_reused_placeholder(self) -> None:
        text = "El asegurado Juan Pérez llamó ayer. Juan Pérez reitera que no tuvo culpa."
        masked, mapping = mask_pii(text)
        assert masked.count("[PERSONA_1]") == 2
        assert "[PERSONA_2]" not in masked
        assert len(mapping) == 1
        assert mapping["[PERSONA_1]"] == "Juan Pérez"


class TestPIIUnmaskingAndReversibility:
    """Test that masked text is cleanly restored without loss of structure."""

    def test_unmask_pii_exact_roundtrip(self) -> None:
        original = (
            "El cliente Carlos Gómez, DNI 44556677T, con vehículo 8901-XYZ y "
            "teléfono 678901234, solicita reparación de luna en Calle Gran Vía 15."
        )
        masked, mapping = mask_pii(original)
        assert masked != original
        restored = unmask_pii(masked, mapping)
        assert restored == original

    def test_unmask_empty_mapping(self) -> None:
        text = "Texto sin ningún token para desanonimizar."
        assert unmask_pii(text, {}) == text

    def test_mask_empty_string(self) -> None:
        masked, mapping = mask_pii("")
        assert masked == ""
        assert mapping == {}


class TestRealisticInsuranceClaimsDoD:
    """DoD Acceptance Criteria: Unit tests with at least 5 realistic insurance claims."""

    def test_claim_1_weather_hail_and_windshield(self) -> None:
        """Caso 1: Tormenta con rotura de lunas y granizo."""
        claim_text = (
            "El asegurado Carlos Gómez Sánchez con DNI 12345678Z declara que debido a la fuerte granizada "
            "del 1 de septiembre, la luna delantera de su vehículo matrícula 4567-KLM sufrió una rotura total. "
            "Teléfono de contacto: 612345678."
        )
        masked, mapping = mask_pii(claim_text)

        # Assertions on privacy
        assert "Carlos Gómez Sánchez" not in masked
        assert "12345678Z" not in masked
        assert "4567-KLM" not in masked
        assert "612345678" not in masked

        # Tokens present
        assert "[PERSONA_1]" in masked
        assert "[DNI_1]" in masked
        assert "[MATRICULA_1]" in masked
        assert "[TELEFONO_1]" in masked

        # Verify exact unmasking
        assert unmask_pii(masked, mapping) == claim_text

    def test_claim_2_two_vehicle_rear_collision(self) -> None:
        """Caso 2: Colisión por alcance con dos partes y datos cruzados."""
        claim_text = (
            "El conductor Juan Pérez con DNI 87654321B y vehículo matrícula 1234-ABC fue alcanzado "
            "por detrás por el vehículo matrícula M-5678-CD conducido por María Rodríguez. "
            "Contacto del tomador: 654987321 y email juan.perez@correo.es."
        )
        masked, mapping = mask_pii(claim_text)

        assert "Juan Pérez" not in masked
        assert "María Rodríguez" not in masked
        assert "87654321B" not in masked
        assert "1234-ABC" not in masked
        assert "M-5678-CD" not in masked
        assert "654987321" not in masked
        assert "juan.perez@correo.es" not in masked

        # Both plates and both persons masked
        assert "[MATRICULA_1]" in masked
        assert "[MATRICULA_2]" in masked
        assert "[PERSONA_1]" in masked
        assert "[PERSONA_2]" in masked

        # Reversibility
        assert unmask_pii(masked, mapping) == claim_text

    def test_claim_3_home_water_leak(self) -> None:
        """Caso 3: Siniestro de hogar por daños por agua."""
        claim_text = (
            "La tomadora Ana Martínez López con DNI 77889900X notifica una fuga de agua en su piso "
            "ubicado en Calle Gran Vía 28, Madrid. Se requiere envío urgente de fontanero. "
            "Teléfono del portero: 912345678."
        )
        masked, mapping = mask_pii(claim_text)

        assert "Ana Martínez López" not in masked
        assert "77889900X" not in masked
        assert "Calle Gran Vía 28, Madrid" not in masked
        assert "912345678" not in masked

        assert unmask_pii(masked, mapping) == claim_text

    def test_claim_4_vehicle_theft_and_vandalism(self) -> None:
        """Caso 4: Robo parcial y vandalismo con cliente extranjero (NIE)."""
        claim_text = (
            "El cliente Pedro Ruiz con NIE X9876543K denuncia la rotura de ventanilla lateral y robo de "
            "pertenencias en su coche matrícula 9988-BZX. Teléfono de contacto: +34 688 99 00 11, "
            "correo electrónico: p.ruiz@guardseguro.es."
        )
        masked, mapping = mask_pii(claim_text)

        assert "Pedro Ruiz" not in masked
        assert "X9876543K" not in masked
        assert "9988-BZX" not in masked
        assert "+34 688 99 00 11" not in masked
        assert "p.ruiz@guardseguro.es" not in masked

        assert unmask_pii(masked, mapping) == claim_text

    def test_claim_5_roadside_assistance_and_indemnity(self) -> None:
        """Caso 5: Asistencia en carretera con perito asignado e IBAN bancario."""
        claim_text = (
            "El asegurado David Navarro con DNI 33445566C solicita indemnización directa en cuenta bancaria "
            "ES91 2100 0418 4502 0005 1332 tras el informe favorable del perito Javier Martín. "
            "Incidente ocurrido en Avda. Diagonal 450, Barcelona."
        )
        masked, mapping = mask_pii(claim_text)

        assert "David Navarro" not in masked
        assert "33445566C" not in masked
        assert "ES91 2100 0418 4502 0005 1332" not in masked
        assert "Javier Martín" not in masked
        assert "Avda. Diagonal 450, Barcelona" not in masked

        assert unmask_pii(masked, mapping) == claim_text

    def test_claim_6_castellana_address_with_clause(self) -> None:
        """Caso 6: Dirección en Paseo de la Castellana seguida de cláusula subordinada."""
        claim_text = (
            "El conductor Antonio Romero Sanz (DNI 12345678Z, móvil 654987321) con domicilio en "
            "Paseo de la Castellana 200, Madrid, conducía el vehículo 1234-BBB cuando se vio involucrado "
            "en una colisión múltiple."
        )
        masked, mapping = mask_pii(claim_text)

        assert "Antonio Romero Sanz" not in masked
        assert "12345678Z" not in masked
        assert "654987321" not in masked
        assert "Paseo de la Castellana 200, Madrid" not in masked
        assert "1234-BBB" not in masked

        assert "[PERSONA_1]" in masked
        assert "[DNI_1]" in masked
        assert "[TELEFONO_1]" in masked
        assert "[DIRECCION_1]" in masked
        assert "[MATRICULA_1]" in masked

        assert unmask_pii(masked, mapping) == claim_text



class TestAnonymizeClaimIntegration:
    """Test integration between PIIMasker and Pydantic domain models."""

    def test_anonymize_claim_helper(self) -> None:
        claim_input = ClaimInput(
            claim_id="CLM-TEST-001",
            raw_text="El cliente Juan Pérez con DNI 12345678Z y matrícula 1234-ABC solicita parte.",
            policy_id="POL-9999",
            policy_type="Auto",
        )

        anonymized = anonymize_claim(claim_input)

        assert anonymized.claim_id == "CLM-TEST-001"
        assert anonymized.original_text == claim_input.raw_text
        assert "Juan Pérez" not in anonymized.anonymized_text
        assert "12345678Z" not in anonymized.anonymized_text
        assert "1234-ABC" not in anonymized.anonymized_text
        assert anonymized.detected_entities_count == 3
        assert len(anonymized.pii_mapping) == 3
        assert anonymized.pii_mapping["[PERSONA_1]"] == "Juan Pérez"
        assert anonymized.pii_mapping["[DNI_1]"] == "12345678Z"
        assert anonymized.pii_mapping["[MATRICULA_1]"] == "1234-ABC"

    def test_pii_masker_custom_toggle(self) -> None:
        """Verify selective disabling of entity types."""
        masker_no_phone = PIIMasker(enable_phone=False)
        text = "Juan Pérez teléfono 612345678."
        masked, mapping = masker_no_phone.mask(text)

        assert "[PERSONA_1]" in masked
        assert "612345678" in masked  # Phone not masked
        assert "[TELEFONO_1]" not in masked
