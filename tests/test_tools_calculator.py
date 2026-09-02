"""Unit tests for Repair Cost Estimation and Baremo Tool (US-05)."""

import json
from pathlib import Path

import pytest

from src.core.models import CostBreakdown, DamageSeverity
from src.tools.repair_calculator import (
    calculate_repair_estimate,
    compute_repair_estimate,
    load_repair_rates,
    normalize_severity,
)


class TestRepairRatesCatalogStructure:
    """Tests for repair baremo catalog loading, schema validation, and fallback mechanisms."""

    def test_load_default_rates_catalog(self):
        rates = load_repair_rates()
        assert "zones" in rates
        assert "currency" in rates
        assert rates["currency"] == "EUR"
        assert len(rates["zones"]) >= 5

    def test_required_dod_zones_present(self):
        rates = load_repair_rates()
        zones = rates["zones"]
        required_zones = ["chapa", "pintura", "luna_delantera", "parachoques", "motor"]
        for required in required_zones:
            assert required in zones, f"Missing required DoD zone '{required}' in repair_rates.json"

    def test_severities_schema_and_cost_integrity(self):
        rates = load_repair_rates()
        required_severities = ["Leve", "Moderado", "Grave"]

        for zone_name, zone_data in rates["zones"].items():
            assert "name" in zone_data
            assert "severities" in zone_data
            severities = zone_data["severities"]

            for sev in required_severities:
                assert sev in severities, f"Missing severity '{sev}' in zone '{zone_name}'"
                entry = severities[sev]
                assert "materials" in entry
                assert "labor" in entry
                assert "description" in entry
                assert entry["materials"] >= 0.0
                assert entry["labor"] >= 0.0
                assert len(entry["description"]) > 5

    def test_fallback_on_invalid_catalog_path(self):
        fallback = load_repair_rates("/invalid/path/that/does/not/exist.json")
        assert "zones" in fallback
        assert "chapa" in fallback["zones"]


class TestSeverityNormalization:
    """Tests for robust normalization of severity strings and enums."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("Leve", "Leve"),
            ("leve", "Leve"),
            ("LEVE", "Leve"),
            ("light", "Leve"),
            ("baja", "Leve"),
            ("1", "Leve"),
            (DamageSeverity.LIGHT, "Leve"),
            ("Moderado", "Moderado"),
            ("moderado", "Moderado"),
            ("MODERADO", "Moderado"),
            ("moderate", "Moderado"),
            ("medio", "Moderado"),
            ("2", "Moderado"),
            (DamageSeverity.MODERATE, "Moderado"),
            ("Grave", "Grave"),
            ("grave", "Grave"),
            ("GRAVE", "Grave"),
            ("severo", "Grave"),
            ("severe", "Grave"),
            ("alta", "Grave"),
            ("3", "Grave"),
            (DamageSeverity.SEVERE, "Grave"),
            ("desconocido_fallback", "Moderado"),
        ],
    )
    def test_normalize_severity_inputs(self, input_val, expected):
        assert normalize_severity(input_val) == expected


class TestComputeRepairEstimateMath:
    """Tests for exact mathematical calculation: Coste Total = Materiales + Mano de Obra - Franquicia."""

    @pytest.mark.parametrize(
        "zone_input,severity,deductible,expected_materials,expected_labor",
        [
            ("chapa", "Leve", 0.0, 45.0, 110.0),
            ("chapa", "Moderado", 150.0, 160.0, 275.0),
            ("chapa", "Grave", 150.0, 480.0, 550.0),
            ("pintura", "Leve", 0.0, 60.0, 82.5),
            ("pintura", "Moderado", 150.0, 150.0, 220.0),
            ("pintura", "Grave", 150.0, 350.0, 440.0),
            ("luna delantera", "Leve", 0.0, 30.0, 60.0),
            ("parabrisas", "Moderado", 0.0, 240.0, 110.0),
            ("luna delantera", "Grave", 0.0, 420.0, 165.0),
            ("parachoques", "Leve", 0.0, 50.0, 90.0),
            ("parachoques delantero", "Moderado", 150.0, 220.0, 180.0),
            ("parachoques trasero", "Grave", 150.0, 450.0, 260.0),
            ("motor", "Leve", 0.0, 120.0, 130.0),
            ("motor", "Moderado", 0.0, 480.0, 330.0),
            ("motor", "Grave", 0.0, 1600.0, 770.0),
            ("cerradura", "Grave", 0.0, 280.0, 165.0),
            ("fontaneria", "Moderado", 0.0, 180.0, 220.0),
            ("cristal ventana", "Moderado", 0.0, 180.0, 110.0),
            ("albanileria", "Leve", 0.0, 40.0, 82.5),
        ],
    )
    def test_compute_repair_estimate_exact_math(
        self,
        zone_input,
        severity,
        deductible,
        expected_materials,
        expected_labor,
    ):
        breakdown, meta = compute_repair_estimate(
            damaged_zone=zone_input,
            severity=severity,
            deductible=deductible,
        )
        assert breakdown.materials == expected_materials
        assert breakdown.labor == expected_labor

        expected_gross = round(expected_materials + expected_labor, 2)
        assert breakdown.gross_total == expected_gross

        expected_net = round(max(0.0, expected_gross - deductible), 2)
        assert breakdown.deductible == deductible
        assert breakdown.net_total == expected_net
        assert len(meta["description"]) > 5

    def test_deductible_exceeding_gross_cost_yields_zero_net(self):
        # When deductible (e.g. 500€) exceeds gross cost (e.g. 155€)
        breakdown, _ = compute_repair_estimate(
            damaged_zone="chapa",
            severity="Leve",
            deductible=500.0,
        )
        assert breakdown.gross_total == 155.0
        assert breakdown.deductible == 500.0
        assert breakdown.net_total == 0.0

    def test_negative_deductible_is_clamped_to_zero(self):
        breakdown, _ = compute_repair_estimate(
            damaged_zone="chapa",
            severity="Leve",
            deductible=-50.0,
        )
        assert breakdown.deductible == 0.0
        assert breakdown.net_total == breakdown.gross_total


class TestCalculateRepairEstimateTool:
    """Tests for the LangChain @tool calculate_repair_estimate."""

    def test_tool_direct_call_returns_valid_json(self):
        json_str = calculate_repair_estimate.invoke({
            "damaged_zone": "parachoques delantero",
            "severity": "Moderado",
            "deductible": 150.0,
        })
        assert isinstance(json_str, str)

        data = json.loads(json_str)
        assert "materiales" in data
        assert "mano_de_obra" in data
        assert "coste_bruto" in data
        assert "franquicia" in data
        assert "total_a_pagar" in data
        assert "zona_afectada" in data
        assert "gravedad" in data
        assert "detalle" in data

        # Math verification
        assert data["materiales"] == 220.0
        assert data["mano_de_obra"] == 180.0
        assert data["coste_bruto"] == 400.0
        assert data["franquicia"] == 150.0
        assert data["total_a_pagar"] == 250.0

    def test_tool_integration_with_cost_breakdown_model(self):
        json_str = calculate_repair_estimate.invoke({
            "damaged_zone": "rotura parabrisas luna delantera",
            "severity": "Leve",
            "deductible": 0.0,
        })
        data = json.loads(json_str)

        # Deserialize into CostBreakdown model
        model = CostBreakdown(
            materials=data["materials"],
            labor=data["labor"],
            deductible=data["deductible"],
        )
        assert model.gross_total == 90.0
        assert model.net_total == 90.0
        assert model.deductible == 0.0

    def test_tool_realistic_insurance_scenarios(self):
        # Scenario 1: Hail damage on roof and hood (Chapa Moderado)
        res1 = json.loads(calculate_repair_estimate.invoke({
            "damaged_zone": "techo y capó abollados por granizo",
            "severity": "Moderado",
            "deductible": 0.0,
        }))
        assert res1["coste_bruto"] == 435.0
        assert res1["total_a_pagar"] == 435.0

        # Scenario 2: Key scratch along door (Pintura Leve, deductible 150€)
        res2 = json.loads(calculate_repair_estimate.invoke({
            "damaged_zone": "rayón intencionado de pintura con llave",
            "severity": "Leve",
            "deductible": 150.0,
        }))
        assert res2["coste_bruto"] == 142.5
        assert res2["total_a_pagar"] == 0.0  # Franchise exceeds gross cost

        # Scenario 3: Broken windshield replacement (Luna delantera Moderado)
        res3 = json.loads(calculate_repair_estimate.invoke({
            "damaged_zone": "parabrisas con grieta",
            "severity": "Moderado",
            "deductible": 0.0,
        }))
        assert res3["coste_bruto"] == 350.0
        assert res3["total_a_pagar"] == 350.0
