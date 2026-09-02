"""Unit tests for assess_claim_risk_and_dispute tool and risk evaluator."""

import json
from src.tools.risk_assessor import (
    assess_claim_risk_and_dispute,
    evaluate_claim_risk,
)


class TestRiskAssessorTool:
    """Test claim risk and dispute analysis tool."""

    def test_clean_claim_without_dispute(self) -> None:
        text = "Impacto de gravilla en luna delantera circulando por autovía."
        eval_result = evaluate_claim_risk(text)

        assert eval_result.requires_expert_appraisal is False
        assert eval_result.risk_level == "Bajo"
        assert len(eval_result.alerts) == 0

    def test_claim_with_contradictory_versions_and_complaint(self) -> None:
        text = (
            "Colisión múltiple con terceros. Existen versiones contradictorias sobre la prioridad de paso, "
            "posible exceso de velocidad y daños estructurales severos en el chasis y motor. "
            "Los terceros implicados han presentado denuncia y no hay atestado policial concluyente."
        )
        eval_result = evaluate_claim_risk(text)

        assert eval_result.requires_expert_appraisal is True
        assert eval_result.risk_level == "Alto"
        assert len(eval_result.alerts) >= 3
        assert any("contradictorias" in a.lower() for a in eval_result.alerts)
        assert any("denuncia" in a.lower() for a in eval_result.alerts)
        assert any("chasis" in a.lower() or "estructurales" in a.lower() for a in eval_result.alerts)

    def test_tool_json_serialization(self) -> None:
        text = "Discrepancia en la versión del accidente y sin atestado policial."
        raw_output = assess_claim_risk_and_dispute.invoke({"claim_text": text})
        data = json.loads(raw_output)

        assert data["requiere_peritaje"] is True
        assert "alertas_detectadas" in data
        assert len(data["alertas_detectadas"]) >= 1
        assert "recomendacion_accion" in data

    def test_claim_with_lack_of_maintenance_and_chronic_leak(self) -> None:
        text = (
            "Goteras y filtraciones continuadas desde hace más de un año debido a la corrosión natural "
            "de los canalones y el desgaste por falta de mantenimiento en el tejado."
        )
        eval_result = evaluate_claim_risk(text)
        assert eval_result.requires_expert_appraisal is True
        assert len(eval_result.alerts) >= 2
        assert any("mantenimiento" in a.lower() for a in eval_result.alerts)
        assert any("más de un año" in a.lower() or "dilación" in a.lower() for a in eval_result.alerts)

