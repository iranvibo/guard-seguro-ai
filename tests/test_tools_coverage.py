"""Unit tests for Policy Coverage Verification Tool (US-04)."""

import json
from pathlib import Path

import pytest

from src.core.models import CoverageCheckResult
from src.tools.policy_coverage import (
    check_policy_coverage,
    load_policy_catalog,
    verify_policy_coverage,
)


class TestPolicyCatalogStructure:
    """Tests for policy catalog loading and JSON integrity."""

    def test_load_default_catalog(self):
        catalog = load_policy_catalog()
        assert "policy_categories" in catalog
        assert "policy_exclusions" in catalog
        assert "default_unknown_response" in catalog
        assert len(catalog["policy_categories"]) >= 5
        assert len(catalog["policy_exclusions"]) >= 3

    def test_catalog_category_schema_completeness(self):
        catalog = load_policy_catalog()
        for category in catalog["policy_categories"]:
            assert "id" in category
            assert "name" in category
            assert "policy_types" in category
            assert "is_covered" in category
            assert "standard_deductible" in category
            assert "conditions" in category
            assert "keywords" in category
            assert isinstance(category["keywords"], list)
            assert len(category["keywords"]) > 0

    def test_catalog_fallback_on_invalid_path(self):
        fallback = load_policy_catalog("/path/that/does/not/exist.json")
        assert "default_unknown_response" in fallback
        assert fallback["default_unknown_response"]["is_covered"] is False


class TestVerifyPolicyCoverageCovered:
    """Tests for covered claims across different damage and incident types."""

    @pytest.mark.parametrize(
        "damage_input,expected_type,expected_deductible",
        [
            ("Rotura de parabrisas delantero por impacto de piedra", "Rotura de lunas", 0.0),
            ("Luneta trasera agrietada", "Rotura de lunas", 0.0),
            ("Impacto severo de granizo en el techo y capó", "Fenómenos atmosféricos y Granizo", 0.0),
            ("Tormenta y pedrisco causaron abolladuras", "Fenómenos atmosféricos y Granizo", 0.0),
            ("Colisión trasera por alcance en semáforo", "Colisión y Daños Propios", 150.0),
            ("Golpe frontal contra otro vehículo en cruce", "Colisión y Daños Propios", 150.0),
            ("Robo total del vehículo en aparcamiento", "Robo y Hurto", 0.0),
            ("Cerradura del conductor forzada en intento de robo", "Robo y Hurto", 0.0),
            ("Rayón intencionado con llave a lo largo de las puertas", "Vandalismo y Actos Malintencionados", 150.0),
            ("Retrovisor arrancado por actos vandálicos", "Vandalismo y Actos Malintencionados", 150.0),
            ("Pinchazo de neumático y solicitud de grúa en autopista", "Asistencia en Carretera y Remolque", 0.0),
            ("Batería descargada y vehículo inmovilizado", "Asistencia en Carretera y Remolque", 0.0),
            ("Fuga de agua en tubería empotrada del baño", "Daños por Agua y Fugas", 0.0),
            ("Incendio en el compartimento del motor con llamas", "Incendio y Explosión", 0.0),
            ("Daños materiales ocasionados a un tercero perjudicado", "Responsabilidad Civil a Terceros", 0.0),
        ],
    )
    def test_covered_damage_types(self, damage_input, expected_type, expected_deductible):
        result = verify_policy_coverage(damage_input, policy_type="Auto" if "baño" not in damage_input else "Hogar")
        assert isinstance(result, CoverageCheckResult)
        assert result.is_covered is True
        assert result.coverage_type == expected_type
        assert result.standard_deductible == expected_deductible
        assert len(result.conditions) > 10


class TestVerifyPolicyCoverageExclusions:
    """Tests for policy exclusions (not covered cases)."""

    @pytest.mark.parametrize(
        "damage_input,expected_exclusion_keyword",
        [
            ("Desgaste natural de los neumáticos por uso prolongado", "Desgaste"),
            ("Avería en el embrague por desgaste paulatino y falta de mantenimiento", "Desgaste"),
            ("Accidente tras dar positivo en control de alcoholemia y consumo de alcohol", "Alcohol"),
            ("Choque ocurrido durante la participación en carreras ilegales nocturnas", "Negligencia"),
            ("Daño deliberado provocado por el propio asegurado con intención de dolo", "Negligencia"),
        ],
    )
    def test_excluded_damage_types(self, damage_input, expected_exclusion_keyword):
        result = verify_policy_coverage(damage_input, policy_type="Auto")
        assert isinstance(result, CoverageCheckResult)
        assert result.is_covered is False
        assert expected_exclusion_keyword.lower() in result.coverage_type.lower() or "exclusión" in result.coverage_type.lower()
        assert len(result.conditions) > 10

    def test_cross_policy_exclusions(self):
        """Ensure claims for vehicles are excluded under Hogar, and home claims under Auto."""
        # Vehicle damage under Hogar policy
        res_vehicle_in_hogar = verify_policy_coverage("Rotura de parabrisas y chapa del coche", policy_type="Hogar")
        assert res_vehicle_in_hogar.is_covered is False
        assert "Vehículos" in res_vehicle_in_hogar.coverage_type

        # Residential damage under Auto policy
        res_home_in_auto = verify_policy_coverage("Fuga de agua en tuberia empotrada de cocina de la vivienda", policy_type="Auto")
        assert res_home_in_auto.is_covered is False
        assert "Inmuebles" in res_home_in_auto.coverage_type


class TestVerifyPolicyCoverageEdgeCases:
    """Tests for edge cases, missing data and uncatalogued claims."""

    def test_empty_or_whitespace_damage_type(self):
        result_empty = verify_policy_coverage("")
        assert result_empty.is_covered is False
        assert result_empty.coverage_type == "Indeterminado"

        result_spaces = verify_policy_coverage("   ")
        assert result_spaces.is_covered is False
        assert result_spaces.coverage_type == "Indeterminado"

    def test_ambiguous_or_uncatalogued_damage(self):
        result = verify_policy_coverage("Aparición de un objeto misterioso de procedencia desconocida")
        assert result.is_covered is False
        assert "Peritaje" in result.coverage_type
        assert "pericial" in result.conditions.lower()

    def test_case_and_accent_insensitivity(self):
        result1 = verify_policy_coverage("GRANIZO Y PEDRISCO")
        result2 = verify_policy_coverage("granizo y pedrisco")
        result3 = verify_policy_coverage("Granízo y pédrisco")

        assert result1.is_covered is True
        assert result2.is_covered is True
        assert result3.is_covered is True
        assert result1.coverage_type == result2.coverage_type == result3.coverage_type


class TestCheckPolicyCoverageTool:
    """Tests for the LangChain @tool check_policy_coverage."""

    def test_tool_direct_call_returns_json_string(self):
        json_output = check_policy_coverage.invoke({"damage_type": "Rotura de luna delantera"})
        assert isinstance(json_output, str)

        parsed = json.loads(json_output)
        assert "cubierto" in parsed
        assert "condiciones" in parsed
        assert "franquicia_estandar" in parsed
        assert parsed["cubierto"] is True
        assert parsed["franquicia_estandar"] == 0.0
        assert "Rotura de lunas" in parsed["tipo_cobertura"]

    def test_tool_with_exclusion_returns_valid_json(self):
        json_output = check_policy_coverage.invoke({"damage_type": "Conducción bajo efectos del alcohol y colisión"})
        parsed = json.loads(json_output)
        assert parsed["cubierto"] is False
        assert parsed["is_covered"] is False
        assert "Alcohol" in parsed["tipo_cobertura"]

    def test_tool_output_compatible_with_coverage_check_result_model(self):
        json_output = check_policy_coverage.invoke({
            "damage_type": "Golpe en el parachoques trasero contra columna",
            "policy_type": "Auto",
        })
        parsed = json.loads(json_output)
        
        # Verify model compatibility
        model_instance = CoverageCheckResult(
            is_covered=parsed["is_covered"],
            coverage_type=parsed["coverage_type"],
            conditions=parsed["conditions"],
            standard_deductible=parsed["standard_deductible"],
        )
        assert model_instance.is_covered is True
        assert model_instance.standard_deductible == 150.0
