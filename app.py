"""GuardSeguro AI — Entrypoint de la Aplicación Streamlit.

Agente Evaluador de Siniestros con Filtros de IA Responsable (Allianz Spain).
"""

import streamlit as st
from src.core.config import get_settings


def main() -> None:
    """Main application layout and initialization."""
    settings = get_settings()

    st.set_page_config(
        page_title=f"{settings.app_name} | Allianz Spain",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🛡️ GuardSeguro AI")
    st.caption("Agente Evaluador de Siniestros con Gobernanza e IA Responsable · CoE Automation & AI")

    # Status / Readiness banner
    with st.sidebar:
        st.header("⚙️ Estado del Sistema")
        st.write(f"**Entorno:** `{settings.app_env.upper()}`")
        st.write(f"**Modelo LLM:** `{settings.openai_model_name}`")
        if settings.is_api_key_configured:
            st.success("API Key configurada correctamente")
        else:
            st.warning("API Key pendiente de configurar en `.env`")

        st.markdown("---")
        st.markdown(
            "**Módulos del Sistema:**\n"
            "- 🛡️ Privacy & PII Masking\n"
            "- ⚙️ Business Tools (Policy & Estimation)\n"
            "- 🤖 ReAct Agent (LLM Tool Calling)\n"
            "- ⚖️ EU AI Act Compliance"
        )

    st.info(
        "🚀 **Cimientos y Modelos de Datos de GuardSeguro AI listos (US-01 & US-02).**\n\n"
        "La arquitectura modular, contenerización Docker, gestión segura de secretos y contratos "
        "de datos fuertemente tipados (`ClaimInput`, `AnonymizedClaim`, `ClaimAssessment`) "
        "están plenamente operativos y validados mediante tests automatizados."
    )


if __name__ == "__main__":
    main()
