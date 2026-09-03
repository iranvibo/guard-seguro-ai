"""Streamlit visual components and layout renderers for GuardSeguro AI (US-09).

Implements responsive, high-aesthetic UI cards, metric banners, PII diff view,
financial resolution cards, intermediate reasoning steps, and EU AI Act compliance tables.
"""

import html
import json
from typing import Any, Dict, Optional
import streamlit as st
import streamlit.components.v1 as components

from src.agent.observability import format_reasoning_flow_mermaid
from src.compliance.models import ComplianceCheckStatus, EUAIActComplianceReport
from src.core.config import Settings
from src.core.models import AnonymizedClaim, ClaimAssessment, ClaimInput, CoverageStatus


def apply_custom_styles() -> None:
    """Inject custom CSS styling aligned with GuardSeguro enterprise design system and modern dark/light mode."""
    st.markdown(
        """
        <style>
        /* GuardSeguro Corporate Theme & Modern Glassmorphism Styles */
        :root {
            --guardseguro-blue: #003781;
            --guardseguro-light-blue: #007AB3;
            --guardseguro-accent: #00A3E0;
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
            display: inline-flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.18);
            border: 1px solid rgba(255, 255, 255, 0.35);
            border-radius: 20px;
            padding: 0.25rem 0.8rem;
            font-size: 0.8rem;
            font-weight: 600;
            color: #FFFFFF;
            white-space: nowrap;
        }

        .tool-chip-container {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            align-items: center;
            margin-top: 0.4rem;
            margin-bottom: 1rem;
        }

        .tool-chip {
            display: inline-flex;
            align-items: center;
            background: #003781;
            color: #FFFFFF !important;
            padding: 0.35rem 0.85rem;
            border-radius: 20px;
            font-size: 0.82rem;
            font-weight: 600;
            font-family: monospace;
            box-shadow: 0 2px 5px rgba(0, 55, 129, 0.25);
            border: 1px solid rgba(0, 163, 224, 0.5);
            white-space: nowrap;
        }

        .tool-step-num {
            background: rgba(255, 255, 255, 0.25);
            border-radius: 50%;
            width: 18px;
            height: 18px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.7rem;
            font-weight: 800;
            margin-right: 0.35rem;
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

        /* E2E Test Suite Styles */
        .test-card-pass {
            background: rgba(16, 185, 129, 0.05);
            border: 1px solid #10B981;
            border-left: 6px solid #10B981;
            border-radius: 10px;
            padding: 1.2rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.1);
        }

        .test-card-fail {
            background: rgba(239, 68, 68, 0.05);
            border: 1px solid #EF4444;
            border-left: 6px solid #EF4444;
            border-radius: 10px;
            padding: 1.2rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 2px 8px rgba(239, 68, 68, 0.1);
        }

        .badge-pass {
            background-color: #D1FAE5;
            color: #065F46;
            border: 1px solid #34D399;
            padding: 0.3rem 0.75rem;
            border-radius: 8px;
            font-weight: 800;
            font-size: 0.85rem;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .badge-fail {
            background-color: #FEE2E2;
            color: #991B1B;
            border: 1px solid #F87171;
            padding: 0.3rem 0.75rem;
            border-radius: 8px;
            font-weight: 800;
            font-size: 0.85rem;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .criteria-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.4rem 0.6rem;
            border-bottom: 1px solid rgba(0, 55, 129, 0.1);
            font-size: 0.9rem;
        }

        /* Streamlit native component tweaks */
        div[data-testid="stMetricLabel"] {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            line-height: 1.25 !important;
        }

        div[data-testid="stMetricLabel"] > div {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.45rem !important;
            font-weight: 700 !important;
        }

        /* Tab buttons responsive sizing */
        button[data-baseweb="tab"] {
            padding-left: 8px !important;
            padding-right: 8px !important;
            padding-top: 6px !important;
            padding-bottom: 6px !important;
            font-size: 0.87rem !important;
            font-weight: 600 !important;
        }

        div[data-baseweb="tab-list"] {
            gap: 2px !important;
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
                <span class="badge-pill">🏢 GuardSeguro Seguros · CoE Automation & AI</span>
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
        st.caption("GuardSeguro AI · CoE Automation & AI")

    return {"force_deterministic": force_deterministic}


def build_claim_report_json(
    claim_input: ClaimInput,
    anonymized_claim: Optional[AnonymizedClaim],
    assessment: ClaimAssessment,
    compliance_report: Optional[EUAIActComplianceReport] = None,
) -> Dict[str, Any]:
    """Construct structured, auditable JSON representation of the entire claim evaluation.

    Contains:
    - tipo_poliza & id_siniestro
    - descripcion (original & anonimizada con recuento PII)
    - caso_cobertura (estado, resolución, franquicia, desglose de costes, recomendación)
    - comportamiento_agente (herramientas usadas, métricas, qué envió y qué recibió en cada paso, razonamiento)
    - auditoria_eu_ai_act (clasificación de riesgo y certificación si aplica)
    """
    # 1. Format intermediate steps (qué envió, qué recibió, qué pensó el agente)
    formatted_steps = []
    for i, step in enumerate(assessment.intermediate_steps or [], start=1):
        if isinstance(step, dict):
            tool_name = step.get("tool", f"tool_{i}")
            tool_input = step.get("tool_input", {})
            obs = step.get("observation", {})
            thought = step.get("thought") or step.get("log", "")
        elif isinstance(step, (tuple, list)) and len(step) >= 2:
            action, obs = step[0], step[1]
            tool_name = getattr(action, "tool", f"tool_{i}")
            tool_input = getattr(action, "tool_input", {})
            thought = getattr(action, "log", "")
            if isinstance(obs, str):
                try:
                    obs = json.loads(obs)
                except Exception:
                    pass
        else:
            tool_name = getattr(step, "tool", f"tool_{i}")
            tool_input = getattr(step, "tool_input", {})
            obs = getattr(step, "observation", {})
            thought = getattr(step, "thought", "")

        formatted_steps.append({
            "paso": i,
            "herramienta": tool_name,
            "pensamiento": thought,
            "enviado": tool_input,
            "recibido": obs,
        })

    # 2. Coverage case resolution
    cost_breakdown_dict = None
    if assessment.cost_breakdown:
        cost_breakdown_dict = {
            "materiales": assessment.cost_breakdown.materials,
            "mano_de_obra": assessment.cost_breakdown.labor,
            "coste_bruto": assessment.cost_breakdown.gross_total,
            "franquicia": assessment.cost_breakdown.deductible,
            "total_neto": assessment.cost_breakdown.net_total,
        }

    status_val = (
        assessment.status.value
        if hasattr(assessment.status, "value")
        else str(assessment.status)
    )

    caso_cobertura = {
        "estado_dictamen": status_val,
        "tiene_cobertura": assessment.is_covered,
        "resumen_cobertura": assessment.coverage_summary,
        "franquicia_aplicable_eur": assessment.deductible,
        "total_a_indemnizar_eur": assessment.net_payout,
        "desglose_costes": cost_breakdown_dict,
        "recomendacion": assessment.recommendation,
        "fundamentacion_razonamiento": assessment.reasoning,
    }

    # 3. Agent behavior & execution tracing
    tools_called = (
        assessment.metrics.tools_called
        if assessment.metrics and assessment.metrics.tools_called
        else [step["herramienta"] for step in formatted_steps]
    )

    comportamiento_agente = {
        "modelo_llm": assessment.metrics.model_name if assessment.metrics else "gpt-4o-mini",
        "tiempo_ejecucion_segundos": assessment.metrics.execution_time_seconds if assessment.metrics else 0.0,
        "total_tokens": assessment.metrics.total_tokens if assessment.metrics else 0,
        "coste_estimado_usd": assessment.metrics.estimated_cost_usd if assessment.metrics else 0.0,
        "total_herramientas_invocadas": len(tools_called),
        "herramientas_utilizadas": tools_called,
        "pasos_intermedios": formatted_steps,
        "razonamiento_final": assessment.reasoning,
    }

    report_dict: Dict[str, Any] = {
        "id_siniestro": claim_input.claim_id,
        "tipo_poliza": claim_input.policy_type,
        "descripcion": {
            "texto_original": claim_input.raw_text,
            "texto_anonimizado": (
                anonymized_claim.anonymized_text
                if anonymized_claim
                else claim_input.raw_text
            ),
            "entidades_pii_detectadas": (
                anonymized_claim.detected_entities_count if anonymized_claim else 0
            ),
        },
        "caso_cobertura": caso_cobertura,
        "comportamiento_agente": comportamiento_agente,
    }

    if compliance_report:
        report_dict["auditoria_eu_ai_act"] = {
            "clasificacion_riesgo": compliance_report.risk_classification.category.value,
            "supervision_humana_art_14": compliance_report.human_in_the_loop.human_validation_required,
            "certificacion_cumplimiento": compliance_report.is_certified,
            "score_cumplimiento_pct": compliance_report.compliance_score,
        }

    return report_dict


def render_report_header_with_copy_button(
    claim_input: ClaimInput,
    anonymized_claim: Optional[AnonymizedClaim],
    assessment: ClaimAssessment,
    compliance_report: Optional[EUAIActComplianceReport] = None,
) -> None:
    """Render the top header of the assessment report panel with the 'copy inform in json' button."""
    report_dict = build_claim_report_json(
        claim_input=claim_input,
        anonymized_claim=anonymized_claim,
        assessment=assessment,
        compliance_report=compliance_report,
    )
    report_json_str = json.dumps(report_dict, indent=2, ensure_ascii=False)

    col_title, col_btn = st.columns([3, 2])
    with col_title:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 0.2rem;">
                <h2 style="margin: 0; padding: 0; color: #003781; font-weight: 800; font-size: 1.55rem;">
                    📊 Informe Técnico de Evaluación
                </h2>
                <span class="badge-pill" style="background: #003781; color: #fff; font-size: 0.8rem; border-radius: 12px; padding: 2px 10px;">
                    {claim_input.claim_id}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        json_escaped = html.escape(report_json_str)
        button_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: flex-end;
                    align-items: center;
                    height: 42px;
                    background: transparent;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }}
                .copy-btn {{
                    background: linear-gradient(135deg, #003781 0%, #005A9C 100%);
                    color: #FFFFFF;
                    border: 1px solid rgba(0, 163, 224, 0.6);
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 13.5px;
                    font-weight: 600;
                    cursor: pointer;
                    box-shadow: 0 2px 6px rgba(0, 55, 129, 0.25);
                    transition: all 0.2s ease-in-out;
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    user-select: none;
                }}
                .copy-btn:hover {{
                    background: linear-gradient(135deg, #004baf 0%, #007AB3 100%);
                    box-shadow: 0 4px 10px rgba(0, 55, 129, 0.35);
                    transform: translateY(-1px);
                }}
                .copy-btn:active {{
                    transform: translateY(0);
                }}
            </style>
        </head>
        <body>
            <button id="copy-json-btn" class="copy-btn" onclick="copyReportJson()">
                <span id="btn-icon">📋</span>
                <span id="btn-text">copy inform in json</span>
            </button>
            <textarea id="json-source-data" style="display: none;">{json_escaped}</textarea>

            <script>
            function copyReportJson() {{
                const rawJson = document.getElementById("json-source-data").value;
                const btn = document.getElementById("copy-json-btn");
                const btnText = document.getElementById("btn-text");
                const btnIcon = document.getElementById("btn-icon");

                function showSuccess() {{
                    btn.style.background = "linear-gradient(135deg, #059669 0%, #10B981 100%)";
                    btn.style.borderColor = "#34D399";
                    btnIcon.textContent = "✅";
                    btnText.textContent = "¡JSON copiado!";
                    setTimeout(() => {{
                        btn.style.background = "linear-gradient(135deg, #003781 0%, #005A9C 100%)";
                        btn.style.borderColor = "rgba(0, 163, 224, 0.6)";
                        btnIcon.textContent = "📋";
                        btnText.textContent = "copy inform in json";
                    }}, 2500);
                }}

                function fallbackCopy(text) {{
                    const tempTextArea = document.createElement("textarea");
                    tempTextArea.value = text;
                    tempTextArea.style.position = "fixed";
                    tempTextArea.style.top = "0";
                    tempTextArea.style.left = "0";
                    tempTextArea.style.opacity = "0";
                    document.body.appendChild(tempTextArea);
                    tempTextArea.focus();
                    tempTextArea.select();
                    try {{
                        const successful = document.execCommand('copy');
                        if (successful) {{
                            showSuccess();
                        }} else {{
                            alert("No se pudo copiar automáticamente al portapapeles.");
                        }}
                    }} catch (err) {{
                        console.error("Fallback copy error:", err);
                    }}
                    document.body.removeChild(tempTextArea);
                }}

                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(rawJson)
                        .then(showSuccess)
                        .catch(err => fallbackCopy(rawJson));
                }} else {{
                    fallbackCopy(rawJson);
                }}
            }}
            </script>
        </body>
        </html>
        """
        components.html(button_html, height=45)


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

    st.caption("Como gestor de la aseguradora, seleccione la acción a ejecutar sobre esta propuesta:")
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

            if met.tools_called:
                st.markdown("**Secuencia de Herramientas Ejecutadas:**")
                tool_chips = "".join([
                    f"<span class='tool-chip'><span class='tool-step-num'>{idx}</span>🛠️ {tool}</span>"
                    for idx, tool in enumerate(met.tools_called, start=1)
                ])
                st.markdown(f"<div class='tool-chip-container'>{tool_chips}</div>", unsafe_allow_html=True)

        st.markdown("#### 🔄 Pasos Intermedios del Agente (Thought / Action / Observation):")
        if assessment.intermediate_steps:
            for i, step in enumerate(assessment.intermediate_steps, start=1):
                # Robust extraction for dictionary or object/tuple step
                if isinstance(step, dict):
                    tool_name = step.get("tool", f"tool_{i}")
                    tool_input = step.get("tool_input", {})
                    obs = step.get("observation", {})
                    thought = step.get("thought") or step.get("log", "")
                elif isinstance(step, (tuple, list)) and len(step) >= 2:
                    action, obs = step[0], step[1]
                    tool_name = getattr(action, "tool", f"tool_{i}")
                    tool_input = getattr(action, "tool_input", {})
                    thought = getattr(action, "log", "")
                else:
                    tool_name = getattr(step, "tool", f"tool_{i}")
                    tool_input = getattr(step, "tool_input", {})
                    obs = getattr(step, "observation", {})
                    thought = getattr(step, "thought", "")

                with st.expander(f"Paso {i}: Invocación de Herramienta `{tool_name}`", expanded=True):
                    if thought:
                        st.markdown(f"**💭 Razonamiento del Agente:** *{thought}*")

                    col_in, col_out = st.columns(2)
                    with col_in:
                        st.markdown(f"**📥 Parámetros Enviados a `{tool_name}`:**")
                        st.json(tool_input)
                    with col_out:
                        st.markdown(f"**📤 Resultado Devuelto por `{tool_name}`:**")
                        if isinstance(obs, (dict, list)):
                            st.json(obs)
                        else:
                            st.code(str(obs), language="json")
        else:
            st.info("No se registraron pasos intermedios (ejecución directa).")

        # Visual Mermaid Reasoning Diagram
        with st.expander("📊 Diagrama de Flujo del Razonamiento (Mermaid)", expanded=False):
            mermaid_code = format_reasoning_flow_mermaid(assessment)
            st.markdown(mermaid_code)

    with tab_act:
        st.markdown(
            f"""
            <div style="background: rgba(0, 55, 129, 0.08); border-left: 4px solid #003781; padding: 1rem; border-radius: 6px; margin-bottom: 1rem;">
                <h4 style="margin:0; color:#003781;">Clasificación: {compliance_report.risk_classification.category.value}</h4>
                <p style="margin: 0.3rem 0 0 0; font-size: 0.9rem;">
                    <strong>Regulación:</strong> {compliance_report.risk_classification.annex_reference}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_hitl, col_trans, col_priv = st.columns(3)
        with col_hitl:
            st.markdown("**Supervisión Humana (Art. 14):**")
            st.write(f"- Validación Obligatoria: `{'SÍ' if compliance_report.human_in_the_loop.human_validation_required else 'NO'}`")
            st.write(f"- Naturaleza: `{'Propuesta Asistida' if compliance_report.human_in_the_loop.is_proposal else 'Decisión Autónoma'}`")
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


def render_e2e_copy_button(
    claim_input: ClaimInput,
    anonymized_claim: Optional[AnonymizedClaim],
    assessment: ClaimAssessment,
    compliance_report: Optional[EUAIActComplianceReport],
    unique_key: str,
) -> None:
    """Render a unique copy button for a specific test case in the E2E test suite."""
    report_dict = build_claim_report_json(
        claim_input=claim_input,
        anonymized_claim=anonymized_claim,
        assessment=assessment,
        compliance_report=compliance_report,
    )
    report_json_str = json.dumps(report_dict, indent=2, ensure_ascii=False)
    json_escaped = html.escape(report_json_str)

    button_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: flex-end;
                align-items: center;
                height: 38px;
                background: transparent;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            .copy-test-btn {{
                background: linear-gradient(135deg, #003781 0%, #005A9C 100%);
                color: #FFFFFF;
                border: 1px solid rgba(0, 163, 224, 0.6);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12.5px;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 2px 5px rgba(0, 55, 129, 0.2);
                transition: all 0.2s ease-in-out;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                user-select: none;
            }}
            .copy-test-btn:hover {{
                background: linear-gradient(135deg, #004baf 0%, #007AB3 100%);
                box-shadow: 0 4px 8px rgba(0, 55, 129, 0.3);
                transform: translateY(-1px);
            }}
            .copy-test-btn:active {{
                transform: translateY(0);
            }}
        </style>
    </head>
    <body>
        <button id="btn-{unique_key}" class="copy-test-btn" onclick="copyTestJson_{unique_key}()">
            <span id="icon-{unique_key}">📋</span>
            <span id="text-{unique_key}">copy inform in json</span>
        </button>
        <textarea id="src-{unique_key}" style="display: none;">{json_escaped}</textarea>

        <script>
        function copyTestJson_{unique_key}() {{
            const rawJson = document.getElementById("src-{unique_key}").value;
            const btn = document.getElementById("btn-{unique_key}");
            const btnText = document.getElementById("text-{unique_key}");
            const btnIcon = document.getElementById("icon-{unique_key}");

            function showSuccess() {{
                btn.style.background = "linear-gradient(135deg, #059669 0%, #10B981 100%)";
                btn.style.borderColor = "#34D399";
                btnIcon.textContent = "✅";
                btnText.textContent = "¡Copiado!";
                setTimeout(() => {{
                    btn.style.background = "linear-gradient(135deg, #003781 0%, #005A9C 100%)";
                    btn.style.borderColor = "rgba(0, 163, 224, 0.6)";
                    btnIcon.textContent = "📋";
                    btnText.textContent = "copy inform in json";
                }}, 2000);
            }}

            function fallbackCopy(text) {{
                const tempTextArea = document.createElement("textarea");
                tempTextArea.value = text;
                tempTextArea.style.position = "fixed";
                tempTextArea.style.top = "0";
                tempTextArea.style.left = "0";
                tempTextArea.style.opacity = "0";
                document.body.appendChild(tempTextArea);
                tempTextArea.focus();
                tempTextArea.select();
                try {{
                    if (document.execCommand('copy')) {{
                        showSuccess();
                    }}
                }} catch (err) {{
                    console.error(err);
                }}
                document.body.removeChild(tempTextArea);
            }}

            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(rawJson)
                    .then(showSuccess)
                    .catch(() => fallbackCopy(rawJson));
            }} else {{
                fallbackCopy(rawJson);
            }}
        }}
        </script>
    </body>
    </html>
    """
    components.html(button_html, height=42)


def render_e2e_suite_metrics(results: list) -> None:
    """Render the top summary metrics banner for E2E Test Suite."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    pass_rate = round((passed / total * 100), 1) if total > 0 else 0
    total_time = sum(r.execution_time_seconds for r in results)

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Total Tests", total)
    with m2:
        st.metric("Tests Pasados", f"✅ {passed}", delta=f"{pass_rate}% Éxito", delta_color="normal")
    with m3:
        st.metric("Tests Fallados", f"❌ {failed}", delta=None if failed == 0 else f"{failed} con error", delta_color="inverse")
    with m4:
        st.metric("Tasa de Aprobación", f"{pass_rate}%")
    with m5:
        st.metric("Tiempo Total Suite", f"{total_time:.2f} s")


def render_e2e_test_card(result: Any, test_idx: int) -> None:
    """Render a comprehensive result card for an E2E test case comparing actual vs expected."""
    case = result.case
    status_class = "test-card-pass" if result.passed else "test-card-fail"
    status_badge = (
        '<span class="badge-pass">✅ PASS</span>'
        if result.passed
        else '<span class="badge-fail">❌ FAIL</span>'
    )

    col_header, col_btn = st.columns([3, 2])
    with col_header:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.3rem;">
                {status_badge}
                <strong style="font-size: 1.15rem; color: #003781;">{case.icon} {case.case_id}: {case.title}</strong>
                <span class="badge-pill" style="background: #003781; color: #fff; font-size: 0.75rem;">{case.policy_type}</span>
                <span style="color: #6B7280; font-size: 0.85rem;">⏱️ {result.execution_time_seconds:.3f}s</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        if result.assessment and result.claim_input:
            render_e2e_copy_button(
                claim_input=result.claim_input,
                anonymized_claim=result.anonymized_claim,
                assessment=result.assessment,
                compliance_report=result.compliance_report,
                unique_key=f"test_{case.case_id.replace('-', '_')}_{test_idx}",
            )

    if result.error:
        st.error(f"⚠️ **Error en ejecución del test:** `{result.error}`")
        return

    # 3 Validation Criteria Table/Grid
    c1, c2, c3 = st.columns(3)

    # 1. Herramientas a Invocarse
    with c1:
        tools_icon = "✅" if result.tools_passed else "❌"
        expected_tools_str = ", ".join(case.expected_tools)
        actual_tools_str = ", ".join(result.actual_tools) if result.actual_tools else "Ninguna"
        st.markdown(
            f"""
            <div style="background: rgba(0, 55, 129, 0.04); border: 1px solid rgba(0, 55, 129, 0.15); border-radius: 8px; padding: 0.7rem; height: 100%;">
                <div style="font-weight: 700; color: #003781; margin-bottom: 0.3rem;">
                    {tools_icon} 🛠️ 1. Herramientas Llamadas
                </div>
                <div style="font-size: 0.82rem; color: #4B5563;">
                    <strong>Esperadas:</strong> <code>{expected_tools_str}</code><br/>
                    <strong>Observadas:</strong> <code>{actual_tools_str}</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Resolución / Dictamen
    with c2:
        status_icon = "✅" if result.status_passed else "❌"
        st.markdown(
            f"""
            <div style="background: rgba(0, 55, 129, 0.04); border: 1px solid rgba(0, 55, 129, 0.15); border-radius: 8px; padding: 0.7rem; height: 100%;">
                <div style="font-weight: 700; color: #003781; margin-bottom: 0.3rem;">
                    {status_icon} ⚖️ 2. Resolución / Dictamen
                </div>
                <div style="font-size: 0.82rem; color: #4B5563;">
                    <strong>Esperada:</strong> <span style="font-weight: 600;">{case.expected_status}</span><br/>
                    <strong>Observada:</strong> <span style="font-weight: 600;">{result.actual_status}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3. Total a Indemnizar
    with c3:
        payout_icon = "✅" if result.payout_passed else "❌"
        st.markdown(
            f"""
            <div style="background: rgba(0, 55, 129, 0.04); border: 1px solid rgba(0, 55, 129, 0.15); border-radius: 8px; padding: 0.7rem; height: 100%;">
                <div style="font-weight: 700; color: #003781; margin-bottom: 0.3rem;">
                    {payout_icon} 💶 3. Total a Indemnizar
                </div>
                <div style="font-size: 0.82rem; color: #4B5563;">
                    <strong>Esperado:</strong> <span style="font-weight: 600;">{case.expected_payout:.2f} €</span><br/>
                    <strong>Observado:</strong> <span style="font-weight: 600;">{result.actual_payout:.2f} €</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Collapsible Details for Agent Traces
    if result.assessment:
        with st.expander(f"🔍 Ver detalles de ejecución y razonamiento de {case.case_id}", expanded=False):
            st.markdown(f"**📖 Razonamiento:** {result.assessment.reasoning}")
            if result.assessment.intermediate_steps:
                st.markdown("**🔄 Pasos Intermedios:**")
                for s_idx, step in enumerate(result.assessment.intermediate_steps, start=1):
                    t_name = step[0].tool if isinstance(step, (tuple, list)) and len(step) >= 1 else getattr(step, 'tool', f'Paso {s_idx}')
                    st.write(f"- Paso {s_idx}: `{t_name}`")
            if result.compliance_report:
                st.caption(f"Certificación EU AI Act: {'✅ Cumple' if result.compliance_report.is_certified else '⚠️ En Revisión'} | Puntuación: {result.compliance_report.compliance_score}%")

