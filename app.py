"""GuardSeguro AI — Streamlit Interactive Dashboard (US-09).

Agente Evaluador de Siniestros con Filtros de IA Responsable & Gobernanza EU AI Act
Allianz Spain · CoE Automation & AI
"""

import logging
import uuid
import streamlit as st

from src.agent.claim_agent import evaluate_claim_with_compliance
from src.core.config import get_settings
from src.core.models import ClaimInput
from src.privacy.masker import anonymize_claim
from src.ui.components import (
    apply_custom_styles,
    render_header,
    render_privacy_panel,
    render_report_header_with_copy_button,
    render_resolution_panel,
    render_sidebar,
    render_traceability_and_compliance_panel,
)
from src.ui.sample_cases import SAMPLE_CASES, get_sample_case_by_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_session_state() -> None:
    """Initialize session state variables if not already set."""
    if "selected_case_id" not in st.session_state:
        st.session_state.selected_case_id = SAMPLE_CASES[0].case_id
    if "prev_selected_option" not in st.session_state:
        st.session_state.prev_selected_option = SAMPLE_CASES[0].case_id
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "last_error" not in st.session_state:
        st.session_state.last_error = None


def main() -> None:
    """Main application loop."""
    settings = get_settings()

    st.set_page_config(
        page_title="GuardSeguro AI | Allianz Spain",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    apply_custom_styles()
    render_header()
    sidebar_config = render_sidebar(settings)
    init_session_state()

    st.markdown("### 📋 Selección y Entrada de Siniestro")
    st.caption("Seleccione un caso de prueba representativo con 1 clic o redacte una reclamación personalizada.")

    # 1-Click Sample Case Selector
    col_sel, col_policy = st.columns([3, 1])

    case_options = {
        case.case_id: f"{case.icon} {case.title} ({case.category})"
        for case in SAMPLE_CASES
    }
    case_options["CUSTOM"] = "✍️ Caso Personalizado (Texto Libre)"

    with col_sel:
        selected_option = st.selectbox(
            "Seleccionar Caso de Demostración:",
            options=list(case_options.keys()),
            format_func=lambda k: case_options[k],
            index=0,
            key="case_selector_widget",
        )

    # Detect case change to clear previous panel
    if selected_option != st.session_state.get("prev_selected_option"):
        st.session_state.prev_selected_option = selected_option
        st.session_state.last_result = None
        st.session_state.last_error = None

    # Sync selection to text
    if selected_option != "CUSTOM":
        sample = get_sample_case_by_id(selected_option)
        claim_default_text = sample.raw_text
        policy_default_type = sample.policy_type
    else:
        claim_default_text = (
            "El cliente Juan Pérez con DNI 12345678Z y teléfono 612345678 declara siniestro "
            "en Madrid con vehículo 1234-ABC por rotura de luna delantera."
        )
        policy_default_type = "Auto"

    with col_policy:
        policy_type = st.selectbox(
            "Tipo de Póliza:",
            options=["Auto", "Hogar"],
            index=0 if policy_default_type == "Auto" else 1,
            key=f"policy_type_{selected_option}",
        )

    # Claim Input Form
    with st.form("claim_evaluation_form"):
        claim_text_input = st.text_area(
            "Descripción del Siniestro (Entrada del Gestor):",
            value=claim_default_text,
            height=130,
            help="Texto original de la reclamación que puede contener datos personales sensibles (PII).",
        )

        btn_col1, btn_col2 = st.columns([1, 2])
        with btn_col1:
            submitted = st.form_submit_button(
                "🚀 Evaluar Siniestro",
                type="primary",
                use_container_width=True,
            )

    # Execute Evaluation Pipeline upon button click
    if submitted:
        # Clear bottom panel immediately
        st.session_state.last_result = None
        st.session_state.last_error = None

        claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        try:
            claim_input = ClaimInput(
                claim_id=claim_id,
                policy_type=policy_type,
                raw_text=claim_text_input,
            )

            with st.spinner("🔒 Aplicando filtro PII y ejecutando Agente ReAct con trazabilidad..."):
                # 1. PII Masking
                anonymized_claim = anonymize_claim(claim_input)

                # 2. Agent Assessment + EU AI Act Audit
                assessment, compliance_report = evaluate_claim_with_compliance(
                    claim=anonymized_claim,
                    claim_id=claim_id,
                    policy_type=policy_type,
                    force_deterministic=sidebar_config["force_deterministic"],
                    settings=settings,
                )

                st.session_state.last_result = {
                    "claim_input": claim_input,
                    "anonymized_claim": anonymized_claim,
                    "assessment": assessment,
                    "compliance_report": compliance_report,
                }
        except Exception as exc:
            logger.exception("Error executing evaluation for claim %s: %s", claim_id, exc)
            st.session_state.last_error = str(exc)

    # Render Bottom Panel (Results, API Error notices, or Prompt)
    if st.session_state.last_error:
        st.markdown("---")
        st.error(
            f"❌ **Error durante la evaluación del siniestro:**\n\n```\n{st.session_state.last_error}\n```\n\n"
            f"💡 *Para resolverlo, revise su clave `OPENAI_API_KEY` o seleccione el modo **'Deterministic Engine (Offline / Alta Fidelidad)'** en la barra lateral.*",
            icon="🚨",
        )

    elif st.session_state.last_result:
        res = st.session_state.last_result
        claim_in: ClaimInput = res["claim_input"]
        anon_claim: AnonymizedClaim = res["anonymized_claim"]
        assessment_res = res["assessment"]
        comp_rep = res["compliance_report"]

        st.markdown("---")

        # Top of Report Panel: Title & Copy inform in JSON button
        render_report_header_with_copy_button(
            claim_input=claim_in,
            anonymized_claim=anon_claim,
            assessment=assessment_res,
            compliance_report=comp_rep,
        )
        st.markdown("---")

        # 3 Panels
        render_privacy_panel(claim_in, anon_claim)
        st.markdown("---")
        render_resolution_panel(assessment_res)
        st.markdown("---")
        render_traceability_and_compliance_panel(assessment_res, comp_rep)




if __name__ == "__main__":
    main()
