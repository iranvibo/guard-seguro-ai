"""Unit tests for the Knowledge Base and Decision Rules UI tab."""

from unittest.mock import MagicMock, patch

from src.tools.policy_coverage import load_policy_catalog
from src.tools.repair_calculator import load_repair_rates
from src.tools.risk_assessor import DISPUTE_INDICATORS, SEVERITY_AND_FRAUD_INDICATORS
from src.ui.knowledge_tab import render_knowledge_tab


class TestKnowledgeTab:
    """Validate knowledge tab data integrity and rendering."""

    def test_policy_catalog_integrity(self):
        """Verify policy catalog categories and exclusions structure."""
        catalog = load_policy_catalog()
        categories = catalog.get("policy_categories", [])
        exclusions = catalog.get("policy_exclusions", [])

        assert len(categories) >= 8
        assert len(exclusions) >= 4

        for cat in categories:
            assert "id" in cat
            assert "name" in cat
            assert "policy_types" in cat
            assert "conditions" in cat
            assert "keywords" in cat

        for exc in exclusions:
            assert "id" in exc
            assert "name" in exc
            assert "policy_types" in exc
            assert "conditions" in exc
            assert "keywords" in exc

    def test_repair_rates_integrity(self):
        """Verify repair rates catalog has Auto and Hogar zones and valid rates."""
        rates = load_repair_rates()
        zones = rates.get("zones", {})
        hourly_rate = rates.get("standard_labor_rate_hourly", 55.0)

        assert hourly_rate > 0
        assert len(zones) >= 10
        assert "chapa" in zones
        assert "luna_delantera" in zones
        assert "fontaneria" in zones
        assert "cristaleria_hogar" in zones

        for zone_key, zone_data in zones.items():
            assert "name" in zone_data
            assert "policy_types" in zone_data
            assert "severities" in zone_data
            for sev in ["Leve", "Moderado", "Grave"]:
                assert sev in zone_data["severities"]
                sev_info = zone_data["severities"][sev]
                assert sev_info["materials"] >= 0
                assert sev_info["labor"] >= 0
                assert sev_info["estimated_hours"] >= 0

    def test_risk_triggers_integrity(self):
        """Verify dispute and severity/fraud indicators lists."""
        assert len(DISPUTE_INDICATORS) >= 8
        assert len(SEVERITY_AND_FRAUD_INDICATORS) >= 10

        for kw, desc in DISPUTE_INDICATORS:
            assert len(kw) > 0
            assert len(desc) > 0

        for kw, desc in SEVERITY_AND_FRAUD_INDICATORS:
            assert len(kw) > 0
            assert len(desc) > 0

    @patch("streamlit.tabs")
    @patch("streamlit.selectbox")
    @patch("streamlit.text_input")
    def test_render_knowledge_tab_runs_without_error(
        self,
        mock_text_input,
        mock_selectbox,
        mock_tabs,
    ):
        """Verify render_knowledge_tab executes cleanly with mocked streamlit contexts."""
        # Dynamic mock for st.tabs based on arguments passed
        mock_tabs.side_effect = lambda tab_list: [MagicMock() for _ in tab_list]
        mock_selectbox.return_value = "Todos los Ramos"
        mock_text_input.return_value = ""

        # Should execute without any exceptions
        render_knowledge_tab()
