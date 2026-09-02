"""Streamlit visual components and layout renderers for GuardSeguro AI (US-09).

Implements responsive, high-aesthetic UI cards, metric banners, PII diff view,
financial resolution cards, intermediate reasoning steps, and EU AI Act compliance tables.
"""

from typing import Any, Dict, Optional
import streamlit as st

from src.compliance.models import ComplianceCheckStatus, EUAIActComplianceReport
from src.core.config import Settings
from src.core.models import AnonymizedClaim, ClaimAssessment, ClaimInput, CoverageStatus


def apply_custom_styles() -> None:
    """Inject custom CSS styling aligned with Allianz design system and modern dark/light mode."""
    st.markdown(
        """
        <style>
        /* Allianz Corporate Theme & Modern Glassmorphism Styles */
        :root {
            --allianz-blue: #003781;
            --allianz-light-blue: #007AB3;
            --allianz-accent: #00A3E0;
            --card-bg: rgba(255, 255, 255, 0.05);
            --card-border: rgba(0, 55, 129, 0.2);
            --success-color: #10B981;
            --warning-color: #F59E0B;
            --danger-color: #EF4444;
        }

        .main-header-container {
            background: linear-gradient(135deg, #002244 0%, #003781 50%, #005A9C 100%);
            padding: 1.5rem 2rem;
            border-radius: 12px;
            color: #FFFFFF;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 34, 68, 0.25);
            border-left: 6px solid #00A3E0;
        }

        .main-header-title {
            font-size: 2.2rem;
            font-weight: 800;
            margin: 0;
            padding: 0;
            letter-spacing: -0.5px;
            color: #FFFFFF !important;
        }

        .main-header-subtitle {
            font-size: 1.05rem;
            font-weight: 400;
            color: #D1E8FF;
            margin-top: 0.35rem;
            margin-bottom: 0;
        }

        .header-badge-row {
            display: flex;
            gap: 0.6rem;
            margin-top: 0.8rem;
            flex-wrap: wrap;
        }

        .badge-pill {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 20px;
            padding: 0.2rem 0.75rem;
            font-size: 0.8rem;
            font-weight: 600;
            color: #FFFFFF;
        }

        .metric-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 1rem;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }

        .status-badge-approved {
            background-color: #D1FAE5;
            color: #065F46;
            border: 1px solid #34D399;
            padding: 0.35rem 0.8rem;
            border-radius: 8px;
            font-weight: 700;
            display: inline-block;
        }

        .status-badge-denied {
            background-color: #FEE2E2;
            color: #991B1B;
            border: 1px solid #F87171;
            padding: 0.35rem 0.8rem;
            border-radius: 8px;
            font-weight: 700;
            display: inline-block;
        }

        .status-badge-expert {
            background-color: #FEF3C7;
            color: #92400E;
            border: 1px solid #FBBF24;
            padding: 0.35rem 0.8rem;
            border-radius: 8px;
            font-weight: 700;
            display: inline-block;
        }

        .pii-tag {
            background-color: #EEF2FF;
            color: #3730A3;
            border: 1px solid #C7D2FE;
            padding: 0.15rem 0.5rem;
            border-radius: 6px;
            font-family: monospace;
            font-size: 0.85rem;
            margin: 0.15rem;
            display: inline-block;
        }

        .financial-highlight {
            font-size: 1.8rem;
            font-weight: 800;
            color: #003781;
        }

        /* Streamlit native component tweaks */
        div[data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
            font-weight: 700 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """Render the application hero header."""
    st.markdown(
        """
        <div class="main-header-container">
            <h1 class="main-header-title">🛡️ GuardSeguro AI</h1>
            <p class="main-header-subtitle">
                Agente Evaluador de Siniestros con Filtros de IA Responsable & Gobernanza EU AI Act
            </p>
            <div class="header-badge-row">
                <span class="badge-pill">🏢 Allianz Spain · CoE Automation & AI</span>
                <span class="badge-pill">🤖 ReAct Agent + Tool Calling</span>
                <span class="badge-pill">🔒 Filtro PII RGPD Activo</span>
                <span class="badge-pill">⚖️ EU AI Act Ready (Alto Riesgo)</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(settings: Settings) -> Dict[str, Any]:
    """Render the sidebar with system parameters and configuration toggles."""
    with st.sidebar:
        st.header("⚙️ Configuración & Estado")

        # Execution Mode Selector
        exec_mode = st.radio(
            "Modo de Ejecución del Agente:",
            options=["Deterministic Engine (Offline / Alta Fidelidad)", "OpenAI GPT-4o-mini (API Real)"],
            index=0 if not settings.is_api_key_configured else 1,
            help="El modo determinista ejecuta las mismas herramientas de negocio sin coste de tokens de API externa.",
        )
        force_deterministic = "Deterministic" in exec_mode

        st.markdown("---")
        st.subheader("📊 Diagnóstico del Sistema")
        st.write(f"**Entorno:** `{settings.app_env.upper()}`")
        st.write(f"**Modelo Configurado:** `{settings.openai_model_name}`")

        if settings.is_api_key_configured:
            st.success("🟢 OpenAI API Key Configurada", icon="✅")
        else:
            st.info("⚪ Sin API Key (Operando en modo Determinista)", icon="ℹ️")

        st.markdown("---")
        st.subheader("📚 Módulos en Producción")
        st.markdown(
            """
            - **US-01 / US-02:** Cimientos Docker & Pydantic v2
            - **US-03:** Privacidad & Enmascaramiento PII
            - **US-04:** Verificación Coberturas de Póliza
            - **US-05:** Baremos y Cálculo de Reparación
            - **US-06:** ReAct Agent (Tool Calling)
            - **US-07:** Trazabilidad & Observabilidad
            - **US-08:** Auditoría Regulatoria EU AI Act
            - **US-09:** Dashboard Interactivo Streamlit
            """
        )

        st.markdown("---")
        st.caption("GuardSeguro AI · Allianz Spain CoE Automation & AI")

    return {"force_deterministic": force_deterministic}


def render_privacy_panel(claim_input: ClaimInput, anonymized_claim: AnonymizedClaim) -> None:
    """Render Panel 1: Privacy and PII masking comparison."""
    st.markdown("### 🔒 1. Privacidad e IA Responsable (US-03)")
    st.caption("Enmascaramiento de datos de carácter personal antes de interactuar con el modelo LLM.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Entidades PII Detectadas", anonymized_claim.detected_entities_count)
    with col2:
        st.metric("Estado de Anonimización", "Protegido (RGPD)", delta="100% Sanitizado")
    with col3:
        st.metric("ID Siniestro", anonymized_claim.claim_id)

    tab_compare, tab_mapping = st.tabs(["📝 Comparativa Texto (Original vs Seguro)", "🏷️ Diccionario de Pseudo-tokens"])

    with tab_compare:
        col_orig, col_mask = st.columns(2)
        with col_orig:
            st.markdown("**Texto Original (Entrada del Gestor con PII Expuesta):**")
            st.text_area(
                "Original",
                value=claim_input.raw_text,
                height=160,
                disabled=True,
                label_visibility="collapsed",
            )
        with col_mask:
            st.markdown("**Texto Anonimizado (Transmitido al Agente LLM):**")
            st.text_area(
                "Anonimizado",
                value=anonymized_claim.anonymized_text,
                height=160,
                disabled=True,
                label_visibility="collapsed",
            )

    with tab_mapping:
        if anonymized_claim.pii_mapping:
            st.markdown("**Mapeo Reversible de Entidades Sanitizadas:**")
            mapping_data = [
                {"Pseudo-Token": token, "Valor Original Protegido": val}
                for token, val in anonymized_claim.pii_mapping.items()
            ]
            st.table(mapping_data)
        else:
            st.info("No se detectaron entidades sensibles de PII en el texto introducido.")


def render_resolution_panel(assessment: ClaimAssessment) -> None:
    """Render Panel 2: Claim resolution, financial breakdown, and human-in-the-loop actions."""
    st.markdown("### 💼 2. Resolución y Dictamen Técnico (US-04, US-05, US-06)")
    st.caption("Dictamen generado por el agente ReAct tras verificar póliza y baremos de reparación.")

    # Status Banner
    status_map = {
        CoverageStatus.APPROVED: ("status-badge-approved", "✅ APROBADO CON COBERTURA", "success"),
        CoverageStatus.DENIED: ("status-badge-denied", "🚫 DENEGADO / EXCLUIDO", "error"),
        CoverageStatus.REQUIRES_EXPERT: ("status-badge-expert", "🔍 REQUIERE PERITAJE TÉCNICO", "warning"),
    }
    badge_class, badge_text, alert_type = status_map.get(
        assessment.status,
        ("status-badge-expert", f"ℹ️ {assessment.status.value}", "info"),
    )

    st.markdown(
        f"""
        <div style="margin-bottom: 1rem;">
            <span class="{badge_class}">{badge_text}</span>
            <span style="margin-left: 0.8rem; font-weight: 600; color: gray;">Siniestro: {assessment.claim_id}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Financial breakdown metrics
    if assessment.cost_breakdown and assessment.is_covered:
        cb = assessment.cost_breakdown
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("Materiales", f"{cb.materials:,.2f} €")
        with m2:
            st.metric("Mano de Obra", f"{cb.labor:,.2f} €")
        with m3:
            st.metric("Coste Bruto", f"{cb.gross_total:,.2f} €")
        with m4:
            st.metric("Franquicia", f"-{cb.deductible:,.2f} €")
        with m5:
            st.metric(
                "Total a Indemnizar",
                f"{cb.net_total:,.2f} €",
                delta=f"Neto Póliza",
                delta_color="normal",
            )
    else:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Estado de Cobertura", "No Procede Pago" if not assessment.is_covered else "Pendiente Perito")
        with m2:
            st.metric("Franquicia Estimada", f"{assessment.deductible:,.2f} €")
        with m3:
            st.metric("Importe Propuesto", f"{assessment.net_payout:,.2f} €")

    # Summary & Reasoning
    st.markdown("**Resumen Ejecutivo:**")
    st.info(assessment.coverage_summary)

    with st.expander("📖 Fundamentación Técnica y Razonamiento del Agente", expanded=True):
        st.write(assessment.reasoning)

    # Human-in-the-loop block (Art. 14 EU AI Act)
    st.markdown("#### 👤 Supervisión Humana (Human-in-the-Loop)")
    st.markdown(f"**Recomendación del Asistente:** *{assessment.recommendation}*")

    st.caption("Como gestor de Allianz, seleccione la acción a ejecutar sobre esta propuesta:")
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    with btn_col1:
        if st.button("✅ Validar y Aprobar", use_container_width=True, type="primary"):
            st.toast(f"Propuesta para {assessment.claim_id} validada y aprobada por el gestor.", icon="✅")
    with btn_col2:
        if st.button("📝 Ajustar Importe", use_container_width=True):
            st.toast("Modo de edición manual activado para el gestor.", icon="✏️")
    with btn_col3:
        if st.button("🔍 Asignar a Perito", use_container_width=True):
            st.toast(f"Orden de peritaje presencial enviada a red pericial.", icon="🔍")
    with btn_col4:
        if st.button("🚫 Rechazar Siniestro", use_container_width=True):
            st.toast(f"Resolución de denegación notificada al asegurado.", icon="📬")


def render_traceability_and_compliance_panel(
    assessment: ClaimAssessment,
    compliance_report: EUAIActComplianceReport,
) -> None:
    """Render Panel 3: Observability traces, tool calling tree, and EU AI Act compliance report."""
    st.markdown("### ⚖️ 3. Trazabilidad, Observabilidad & EU AI Act (US-07 & US-08)")
    st.caption("Auditoría técnica del flujo de razonamiento y certificación de cumplimiento normativo.")

    tab_obs, tab_act, tab_raw = st.tabs(
        ["🔍 Observabilidad & Razonamiento (US-07)", "📜 Ficha EU AI Act (US-08)", "💾 Exportar Datos"]
    )

    with tab_obs:
        if assessment.metrics:
            met = assessment.metrics
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Tiempo de Inferencia", f"{met.execution_time_seconds:.3f} s")
            with c2:
                st.metric("Total Tokens", f"{met.total_tokens:,}")
            with c3:
                st.metric("Coste Estimado", f"${met.estimated_cost_usd:.6f}")
            with c4:
                st.metric("Herramientas Invocadas", f"{met.tools_count} tools")

        st.markdown("#### 🔄 Pasos Intermedios del Agente (Thought / Action / Observation):")
        if assessment.intermediate_steps:
            for i, step in enumerate(assessment.intermediate_steps, start=1):
                tool_name = step.tool_name if hasattr(step, "tool_name") else str(step[0].tool if isinstance(step, (tuple, list)) else "Herramienta")
                with st.expander(f"Paso {i}: Invocación de Herramienta `{tool_name}`", expanded=(i == 1)):
                    if hasattr(step, "tool_input"):
                        st.json({"tool": step.tool_name, "input": step.tool_input, "output": step.tool_output})
                    elif isinstance(step, (tuple, list)) and len(step) >= 2:
                        action, obs = step[0], step[1]
                        st.markdown(f"**Herramienta:** `{getattr(action, 'tool', 'N/A')}`")
                        st.markdown(f"**Parámetros:** `{getattr(action, 'tool_input', 'N/A')}`")
                        st.markdown("**Respuesta Obtenida:**")
                        st.code(str(obs), language="json")
        else:
            st.info("No se registraron pasos intermedios (ejecución directa).")

    with tab_act:
        st.markdown(
            f"""
            <div style="background: rgba(0, 55, 129, 0.08); border-left: 4px solid #003781; padding: 1rem; border-radius: 6px; margin-bottom: 1rem;">
                <h4 style="margin:0; color:#003781;">Clasificación: {compliance_report.risk_classification.category.value}</h4>
                <p style="margin: 0.3rem 0 0 0; font-size: 0.9rem;">
                    <strong>Regulación:</strong> {compliance_report.risk_classification.eu_ai_act_annex} | 
                    <strong>Marco Legal:</strong> {compliance_report.risk_classification.legal_basis}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_hitl, col_trans, col_priv = st.columns(3)
        with col_hitl:
            st.markdown("**Supervisión Humana (Art. 14):**")
            st.write(f"- Validación Obligatoria: `{'SÍ' if compliance_report.human_in_the_loop.human_validation_required else 'NO'}`")
            st.write(f"- Naturaleza: `{compliance_report.human_in_the_loop.decision_nature}`")
        with col_trans:
            st.markdown("**Transparencia (Art. 12/13):**")
            st.write(f"- Trazabilidad Activa: `{'SÍ' if compliance_report.transparency_audit.has_traceability_logs else 'NO'}`")
            st.write(f"- Modelo: `{compliance_report.transparency_audit.model_name}`")
        with col_priv:
            st.markdown("**Privacidad (Art. 10 & RGPD):**")
            st.write(f"- Enmascaramiento PII: `{'SÍ' if compliance_report.privacy_audit.pii_masking_applied else 'NO'}`")
            st.write(f"- Entidades Anonimizadas: `{compliance_report.privacy_audit.detected_entities_count}`")

        st.markdown("#### 📋 Matriz de Controles y Evidencias:")
        table_rows = []
        for check in compliance_report.checks:
            table_rows.append(
                {
                    "Artículo": check.article_reference,
                    "Control de Gobernanza": check.name,
                    "Estado": "✅ Cumple" if check.status == ComplianceCheckStatus.COMPLIANT else str(check.status.value),
                    "Evidencia Técnica": check.evidence,
                }
            )
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    with tab_raw:
        st.markdown("#### 📥 Descarga de Auditoría y Dictamen")
        c_down1, c_down2 = st.columns(2)
        with c_down1:
            st.download_button(
                label="📄 Descargar Dictamen JSON",
                data=assessment.model_dump_json(indent=2),
                file_name=f"dictamen_{assessment.claim_id}.json",
                mime="application/json",
                use_container_width=True,
            )
        with c_down2:
            st.download_button(
                label="📜 Descargar Ficha EU AI Act JSON",
                data=compliance_report.model_dump_json(indent=2),
                file_name=f"ficha_eu_ai_act_{assessment.claim_id}.json",
                mime="application/json",
                use_container_width=True,
            )
