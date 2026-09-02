"""Knowledge Base & Decision Rules Tab for GuardSeguro AI.

Provides an intuitive, highly structured visualization of the domain knowledge,
policy terms, repair baremos, risk indicators, and Responsible AI guidelines
that govern the Agent's claim evaluation decisions.
"""

import streamlit as st

from src.tools.policy_coverage import load_policy_catalog
from src.tools.repair_calculator import load_repair_rates
from src.tools.risk_assessor import DISPUTE_INDICATORS, SEVERITY_AND_FRAUD_INDICATORS


def render_knowledge_tab() -> None:
    """Render the Knowledge Base & Decision Rules tab."""
    st.markdown("### 📚 Base de Conocimiento & Reglas de Decisión del Agente")
    st.caption(
        "Explore las directrices de negocio, condicionados de pólizas, baremos de taller, "
        "indicadores de riesgo y principios de IA Responsable en los que se fundamenta el agente."
    )

    # Global KPI Metrics
    catalog = load_policy_catalog()
    rates = load_repair_rates()
    categories = catalog.get("policy_categories", [])
    exclusions = catalog.get("policy_exclusions", [])
    zones = rates.get("zones", {})
    hourly_rate = rates.get("standard_labor_rate_hourly", 55.0)
    total_risk_triggers = len(DISPUTE_INDICATORS) + len(SEVERITY_AND_FRAUD_INDICATORS)

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("📋 Coberturas Tipificadas", len(categories), help="Garantías con cobertura contractual automática.")
    with m2:
        st.metric("🚫 Exclusiones de Póliza", len(exclusions), help="Causas tipificadas de denegación directa.")
    with m3:
        st.metric("🛠️ Zonas Baremadas", len(zones), help="Piezas y áreas con tarifas de materiales y mano de obra.")
    with m4:
        st.metric("⚠️ Disparadores de Riesgo", total_risk_triggers, help="Patrones que activan peritaje presencial o investigación.")
    with m5:
        st.metric("💶 Tarifa M.O. Oficial", f"{hourly_rate:.2f} €/h", help="Tarifa horaria estándar en red de talleres concertados.")

    st.markdown("---")

    # 5 Organized Sub-Tabs
    k_tab1, k_tab2, k_tab3, k_tab4, k_tab5 = st.tabs([
        "🔄 1. Protocolo de Decisión (Flujo ReAct)",
        "📜 2. Catálogo de Coberturas & Exclusiones",
        "💶 3. Baremos Oficiales de Reparación",
        "⚠️ 4. Matriz de Riesgos & Peritaje",
        "🛡️ 5. Gobernanza e IA Responsable",
    ])

    # =========================================================================
    # SUB-TAB 1: PROTOCOLO DE DECISIÓN (FLUJO REACT)
    # =========================================================================
    with k_tab1:
        st.markdown("#### 🎯 Protocolo de Evaluación Secuencial Paso a Paso")
        st.write(
            "El agente sigue un protocolo estricto y determinista en 4 pasos para garantizar decisiones "
            "objetivas, eficientes y alineadas con las directrices de **Allianz Spain**:"
        )

        st.markdown(
            """
            <div style="display: flex; flex-direction: column; gap: 1rem; margin-top: 1rem; margin-bottom: 1.5rem;">
                <!-- Paso 1 -->
                <div style="background: rgba(0, 55, 129, 0.05); border-left: 5px solid #003781; border-radius: 8px; padding: 1rem 1.2rem;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem;">
                        <strong style="color: #003781; font-size: 1.05rem;">
                            1️⃣ Paso 1 — Verificación de Cobertura y Regla de Poda Inmediata (Short-Circuiting)
                        </strong>
                        <span style="background: #003781; color: white; border-radius: 12px; padding: 2px 10px; font-size: 0.75rem; font-family: monospace;">
                            check_policy_coverage
                        </span>
                    </div>
                    <p style="margin: 0; font-size: 0.92rem; color: #1F2937;">
                        Analiza la causa raíz y tipo de daño reportado junto con el ramo de la póliza (Auto vs Hogar).
                    </p>
                    <div style="margin-top: 0.5rem; font-size: 0.88rem; background: rgba(239, 68, 68, 0.08); border-left: 3px solid #EF4444; padding: 0.5rem; border-radius: 4px;">
                        <strong>🛑 Regla de Parada Inmediata (Short-Circuiting):</strong> Si la póliza excluye el daño (ej. desgaste, avería mecánica, alcohol) o no tiene cobertura, el flujo se detiene inmediatamente. Se emite <code>status: 'Denegado'</code> (0,00 €) y <strong>queda estrictamente prohibido invocar herramientas adicionales</strong>.
                    </div>
                </div>

                <!-- Paso 2 -->
                <div style="background: rgba(245, 158, 11, 0.05); border-left: 5px solid #F59E0B; border-radius: 8px; padding: 1rem 1.2rem;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem;">
                        <strong style="color: #92400E; font-size: 1.05rem;">
                            2️⃣ Paso 2 — Evaluación Obligatoria de Riesgos y Controversias
                        </strong>
                        <span style="background: #D97706; color: white; border-radius: 12px; padding: 2px 10px; font-size: 0.75rem; font-family: monospace;">
                            assess_claim_risk_and_dispute
                        </span>
                    </div>
                    <p style="margin: 0; font-size: 0.92rem; color: #1F2937;">
                        <strong>Obligatorio si tiene cobertura:</strong> Evalúa si existen versiones contradictorias, ausencia de atestado policial concluyente, denuncias de terceros, sospechas de fraude o daños estructurales en chasis/inmuebles.
                    </p>
                    <div style="margin-top: 0.5rem; font-size: 0.88rem; background: rgba(245, 158, 11, 0.1); border-left: 3px solid #F59E0B; padding: 0.5rem; border-radius: 4px;">
                        <strong>🔍 Criterio de Peritaje:</strong> Si detecta controversia o daño severo (<code>requiere_peritaje: true</code>), el dictamen se fija en <code>status: 'Requiere Peritaje'</code>, retención cautelar de pago (0,00 €) y <strong>se cancela la estimación automática de baremos</strong>.
                    </div>
                </div>

                <!-- Paso 3 -->
                <div style="background: rgba(16, 185, 129, 0.05); border-left: 5px solid #10B981; border-radius: 8px; padding: 1rem 1.2rem;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem;">
                        <strong style="color: #065F46; font-size: 1.05rem;">
                            3️⃣ Paso 3 — Estimación Económica Oficial de Reparación
                        </strong>
                        <span style="background: #059669; color: white; border-radius: 12px; padding: 2px 10px; font-size: 0.75rem; font-family: monospace;">
                            calculate_repair_estimate
                        </span>
                    </div>
                    <p style="margin: 0; font-size: 0.92rem; color: #1F2937;">
                        <strong>Solo si el siniestro está cubierto y NO requiere peritaje:</strong> Consulta la base de datos de baremos oficiales de Allianz por zona dañada y nivel de gravedad (Leve, Moderado, Grave), deduciendo la franquicia contratada.
                    </p>
                    <div style="margin-top: 0.5rem; font-size: 0.88rem; background: rgba(16, 185, 129, 0.1); border-left: 3px solid #10B981; padding: 0.5rem; border-radius: 4px;">
                        <strong>⚡ Regla de Eficiencia (Cero Redundancia):</strong> Máximo 1 llamada por siniestro estándar (o 2 llamadas para granizo multizona: luna delantera + chapa). Tras obtener los importes, se detienen todas las herramientas.
                    </div>
                </div>

                <!-- Paso 4 -->
                <div style="background: rgba(0, 122, 179, 0.05); border-left: 5px solid #007AB3; border-radius: 8px; padding: 1rem 1.2rem;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem;">
                        <strong style="color: #007AB3; font-size: 1.05rem;">
                            4️⃣ Paso 4 — Dictamen Estructurado JSON & Supervisión Humana
                        </strong>
                        <span style="background: #007AB3; color: white; border-radius: 12px; padding: 2px 10px; font-size: 0.75rem; font-family: monospace;">
                            Art. 14 EU AI Act
                        </span>
                    </div>
                    <p style="margin: 0; font-size: 0.92rem; color: #1F2937;">
                        Emisión del dictamen formal en JSON estricto con desglose económico, razonamiento transparente y propuesta redactada expresamente para la <strong>revisión y validación por el gestor humano</strong> (Human-in-the-Loop).
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### ⚡ Principios de Ejecución y Eficiencia")
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            st.info("🎯 **Objetividad Contractual:** Utiliza exclusivamente datos oficiales de baremos y condicionados, sin inventar importes.")
        with c_p2:
            st.info("🚫 **Cero Redundancia:** Cada herramienta se invoca como máximo una vez por concepto o zona diferenciada.")
        with c_p3:
            st.info("👤 **Supervisión Obligatoria:** El sistema asiste y propone, garantizando que la decisión final recaiga en el gestor humano.")

    # =========================================================================
    # SUB-TAB 2: CATÁLOGO DE COBERTURAS & EXCLUSIONES
    # =========================================================================
    with k_tab2:
        st.markdown("#### 📜 Catálogo de Coberturas y Exclusiones de Pólizas")
        st.caption("Condicionados generales y reglas contractuales aplicables para los ramos de Automóvil y Hogar.")

        col_filter, col_search = st.columns([1, 2])
        with col_filter:
            branch_filter = st.selectbox(
                "Filtrar por Ramo de Póliza:",
                options=["Todos los Ramos", "Auto 🚗", "Hogar 🏠"],
                index=0,
                key="knowledge_branch_filter",
            )
        with col_search:
            search_query = st.text_input(
                "🔍 Buscar cobertura, daño o palabra clave:",
                placeholder="Ej. granizo, lunas, agua, desgaste, franquicia...",
                key="knowledge_search_query",
            ).strip().lower()

        selected_branch = None
        if "Auto" in branch_filter:
            selected_branch = "Auto"
        elif "Hogar" in branch_filter:
            selected_branch = "Hogar"

        tab_cov, tab_excl = st.tabs(["✅ Coberturas Contractuales Incluidas", "🚫 Exclusiones Expresas de Póliza"])

        # Coberturas Incluidas
        with tab_cov:
            filtered_categories = []
            for cat in categories:
                cat_branches = cat.get("policy_types", [])
                if selected_branch and selected_branch not in cat_branches:
                    continue
                # Search filter
                if search_query:
                    searchable_text = f"{cat.get('name', '')} {cat.get('conditions', '')} {' '.join(cat.get('keywords', []))}".lower()
                    if search_query not in searchable_text:
                        continue
                filtered_categories.append(cat)

            st.write(f"Mostrando **{len(filtered_categories)}** coberturas disponibles:")

            # Table view
            cov_table_data = []
            for cat in filtered_categories:
                cov_table_data.append({
                    "Garantía / Cobertura": cat.get("name"),
                    "Ramos": ", ".join(cat.get("policy_types", [])),
                    "Franquicia Estándar": f"{cat.get('standard_deductible', 0.0):.2f} €",
                    "Condición Principal": cat.get("conditions"),
                    "Palabras Clave (Detección)": ", ".join(cat.get("keywords", [])[:5]) + "...",
                })
            st.dataframe(cov_table_data, use_container_width=True, hide_index=True)

            # Detailed Expanders
            with st.expander("📖 Ver Detalle Completo y Cláusulas Contractuales por Garantía", expanded=False):
                for cat in filtered_categories:
                    st.markdown(f"##### 🛡️ {cat.get('name')} (`{cat.get('id')}`)")
                    st.write(f"- **Ramos amparados:** `{', '.join(cat.get('policy_types', []))}`")
                    st.write(f"- **Franquicia contractual:** `{cat.get('standard_deductible', 0.0):.2f} €`")
                    st.write(f"- **Condicionado:** {cat.get('conditions')}")
                    st.caption(f"Palabras clave de activación: {', '.join(cat.get('keywords', []))}")
                    st.markdown("---")

        # Exclusiones
        with tab_excl:
            filtered_exclusions = []
            for exc in exclusions:
                exc_branches = exc.get("policy_types", [])
                if selected_branch and selected_branch not in exc_branches:
                    continue
                if search_query:
                    searchable_text = f"{exc.get('name', '')} {exc.get('conditions', '')} {' '.join(exc.get('keywords', []))}".lower()
                    if search_query not in searchable_text:
                        continue
                filtered_exclusions.append(exc)

            st.write(f"Mostrando **{len(filtered_exclusions)}** exclusiones contractuales:")

            excl_table_data = []
            for exc in filtered_exclusions:
                excl_table_data.append({
                    "Causa de Exclusión": exc.get("name"),
                    "Ramos Afectados": ", ".join(exc.get("policy_types", [])),
                    "Fundamento Contractual": exc.get("conditions"),
                    "Disparadores": ", ".join(exc.get("keywords", [])[:5]) + "...",
                })
            st.dataframe(excl_table_data, use_container_width=True, hide_index=True)

            with st.expander("📖 Ver Motivos y Términos de Exclusión Expresa", expanded=False):
                for exc in filtered_exclusions:
                    st.markdown(f"##### 🚫 {exc.get('name')}")
                    st.write(f"- **Ramos aplicables:** `{', '.join(exc.get('policy_types', []))}`")
                    st.write(f"- **Justificación de rechazo:** {exc.get('conditions')}")
                    st.caption(f"Disparadores léxicos: {', '.join(exc.get('keywords', []))}")
                    st.markdown("---")

    # =========================================================================
    # SUB-TAB 3: BAREMOS OFICIALES DE REPARACIÓN
    # =========================================================================
    with k_tab3:
        st.markdown("#### 💶 Baremos Oficiales de Reparación y Costes de Taller")
        st.caption("Tablas de cálculo determinista para piezas, materiales y mano de obra con tarifa unificada.")

        st.markdown(
            f"""
            <div style="background: rgba(0, 55, 129, 0.05); border: 1px solid rgba(0, 55, 129, 0.2); border-radius: 8px; padding: 0.9rem 1.2rem; margin-bottom: 1rem;">
                <strong style="color: #003781;">📐 Fórmula Matemática Oficial:</strong>
                <ul style="margin: 0.4rem 0 0 1.2rem; font-size: 0.92rem;">
                    <li><code>Coste Bruto = Materiales (€) + Mano de Obra (€)</code></li>
                    <li><code>Total a Indemnizar (Neto) = max(0.00, Coste Bruto - Franquicia (€))</code></li>
                    <li><strong>Tarifa Horaria de Mano de Obra Allianz:</strong> <code>{hourly_rate:.2f} €/hora</code></li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_b_filter, col_b_zone = st.columns([1, 2])
        with col_b_filter:
            baremo_branch = st.selectbox(
                "Filtrar por Especialidad:",
                options=["Todas las Especialidades", "Auto 🚗", "Hogar 🏠"],
                index=0,
                key="baremo_branch_filter",
            )

        baremo_branch_str = None
        if "Auto" in baremo_branch:
            baremo_branch_str = "Auto"
        elif "Hogar" in baremo_branch:
            baremo_branch_str = "Hogar"

        # Filter zones
        filtered_zones = {}
        for z_key, z_data in zones.items():
            z_branches = z_data.get("policy_types", ["Auto", "Hogar"])
            if baremo_branch_str and baremo_branch_str not in z_branches:
                continue
            filtered_zones[z_key] = z_data

        with col_b_zone:
            zone_options = {"ALL": "📋 Todas las Zonas Baremadas"}
            for zk, zd in filtered_zones.items():
                zone_options[zk] = f"{zd.get('name', zk)} ({', '.join(zd.get('policy_types', []))})"

            selected_zone_key = st.selectbox(
                "Seleccionar Zona Específica:",
                options=list(zone_options.keys()),
                format_func=lambda k: zone_options.get(k, k),
                index=0,
                key="baremo_zone_selector",
            )

        # Build comprehensive baremos table
        table_rows = []
        zones_to_display = (
            filtered_zones
            if selected_zone_key == "ALL"
            else {selected_zone_key: filtered_zones[selected_zone_key]}
            if selected_zone_key in filtered_zones
            else filtered_zones
        )

        for zk, zd in zones_to_display.items():
            z_name = zd.get("name", zk)
            z_branches_str = ", ".join(zd.get("policy_types", []))
            for sev_name, sev_data in zd.get("severities", {}).items():
                mat = float(sev_data.get("materials", 0.0))
                lab = float(sev_data.get("labor", 0.0))
                hours = float(sev_data.get("estimated_hours", 0.0))
                gross = mat + lab
                desc = sev_data.get("description", "")
                table_rows.append({
                    "Zona / Elemento": z_name,
                    "Ramo": z_branches_str,
                    "Gravedad": sev_name,
                    "Horas M.O.": f"{hours:.1f} h",
                    "Materiales (€)": f"{mat:.2f} €",
                    "Mano Obra (€)": f"{lab:.2f} €",
                    "Coste Bruto (€)": f"{gross:.2f} €",
                    "Intervención Técnica": desc,
                })

        st.dataframe(table_rows, use_container_width=True, hide_index=True)

        st.markdown("#### ⚡ Reglas Especiales de Baremos Bipieza / Multizona")
        st.info(
            "🌩️ **Siniestro de Granizo / Tormenta Multizona en Auto:**\n"
            "- Sustitución de parabrisas térmico acústico (`luna_delantera`, Grave): **585,00 €** (420 € mat + 165 € m.o.).\n"
            "- Reparación y conformado de carrocería/capó (`chapa`, Moderado): **435,00 €** (160 € mat + 275 € m.o.).\n"
            "- **Total Consolidado:** **1.020,00 €** (Franquicia 0,00 € por fenómeno meteorológico)."
        )

    # =========================================================================
    # SUB-TAB 4: MATRIZ DE RIESGOS & PERITAJE
    # =========================================================================
    with k_tab4:
        st.markdown("#### ⚠️ Matriz de Riesgos, Controversias y Criterios de Peritaje")
        st.caption(
            "Mecanismos de detección preventiva de controversias de culpabilidad, fraudes y daños estructurales "
            "que motivan la suspensión del pago automático y la derivación a perito presencial."
        )

        st.markdown(
            """
            <div style="background: rgba(245, 158, 11, 0.08); border-left: 5px solid #F59E0B; border-radius: 8px; padding: 1rem; margin-bottom: 1.2rem;">
                <strong style="color: #92400E; font-size: 1rem;">⚖️ Criterio de Retención Cautelar de Pago:</strong>
                <p style="margin: 0.3rem 0 0 0; font-size: 0.92rem; color: #1F2937;">
                    Si la declaración del asegurado contiene <strong>al menos un indicador crítico</strong> de controversia (versiones opuestas, atestado no concluyente, denuncias) o de severidad/fraude (daño en chasis, exceso de velocidad, dilación temporal):
                </p>
                <ul style="margin: 0.3rem 0 0 1.2rem; font-size: 0.9rem;">
                    <li>El dictamen final se clasifica obligatoriamente como <strong><code>Requiere Peritaje</code></strong>.</li>
                    <li>La indemnización directa se fija en <strong><code>0,00 €</code></strong> (pago retenido cautelarmente).</li>
                    <li>Se emite una orden de inspección física presencial o traslado a la asesoría jurídica.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_d1, col_d2 = st.columns(2)

        with col_d1:
            st.markdown("##### ⚔️ 1. Indicadores de Controversia y Falta de Atestado")
            st.caption("Conflictos en la dinámica del siniestro y determinación de culpabilidad.")
            dispute_data = [
                {"Término / Patrón Detectado": kw, "Motivo de Alerta y Riesgo": desc}
                for kw, desc in DISPUTE_INDICATORS
            ]
            st.dataframe(dispute_data, use_container_width=True, hide_index=True)

        with col_d2:
            st.markdown("##### 🚨 2. Indicadores de Severidad, Daños Estructurales y Fraude")
            st.caption("Afectaciones graves a la seguridad, indicios de simulación o daños crónicos.")
            severity_data = [
                {"Término / Patrón Detectado": kw, "Motivo de Alerta y Riesgo": desc}
                for kw, desc in SEVERITY_AND_FRAUD_INDICATORS
            ]
            st.dataframe(severity_data, use_container_width=True, hide_index=True)

    # =========================================================================
    # SUB-TAB 5: GOBERNANZA E IA RESPONSABLE
    # =========================================================================
    with k_tab5:
        st.markdown("#### 🛡️ Filtros de IA Responsable & Gobernanza EU AI Act")
        st.caption("Garantías regulatorias para sistemas de IA clasificados de Alto Riesgo en el sector asegurador.")

        g_col1, g_col2, g_col3 = st.columns(3)

        with g_col1:
            st.markdown(
                """
                <div style="background: rgba(0, 55, 129, 0.05); border-top: 4px solid #003781; border-radius: 8px; padding: 1rem; height: 100%;">
                    <h5 style="color: #003781; margin: 0 0 0.5rem 0;">🔒 Privacidad y RGPD</h5>
                    <p style="font-size: 0.88rem; color: #374151; margin-bottom: 0.5rem;">
                        <strong>Art. 10 EU AI Act & RGPD (UE 2016/679):</strong>
                    </p>
                    <ul style="font-size: 0.85rem; color: #4B5563; padding-left: 1.1rem; margin: 0;">
                        <li>Enmascaramiento obligatorio de PII antes de invocar cualquier LLM.</li>
                        <li>Detección de DNI, NIE, nombres de personas, teléfonos, emails, matrículas y tarjetas de crédito.</li>
                        <li>Sustitución por pseudo-tokens deterministas reversibles en servidor seguro.</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with g_col2:
            st.markdown(
                """
                <div style="background: rgba(0, 122, 179, 0.05); border-top: 4px solid #007AB3; border-radius: 8px; padding: 1rem; height: 100%;">
                    <h5 style="color: #007AB3; margin: 0 0 0.5rem 0;">👤 Human-in-the-Loop</h5>
                    <p style="font-size: 0.88rem; color: #374151; margin-bottom: 0.5rem;">
                        <strong>Art. 14 EU AI Act (Supervisión Humana):</strong>
                    </p>
                    <ul style="font-size: 0.85rem; color: #4B5563; padding-left: 1.1rem; margin: 0;">
                        <li>El agente nunca emite órdenes de pago finales autónomas.</li>
                        <li>Genera propuestas técnicas motivadas dirigidas expresamente al gestor humano.</li>
                        <li>El tramitador tiene facultad de validar, ajustar importes, derivar a perito o rechazar.</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with g_col3:
            st.markdown(
                """
                <div style="background: rgba(16, 185, 129, 0.05); border-top: 4px solid #10B981; border-radius: 8px; padding: 1rem; height: 100%;">
                    <h5 style="color: #065F46; margin: 0 0 0.5rem 0;">🔍 Transparencia & Trazabilidad</h5>
                    <p style="font-size: 0.88rem; color: #374151; margin-bottom: 0.5rem;">
                        <strong>Art. 12 y 13 EU AI Act (Auditabilidad):</strong>
                    </p>
                    <ul style="font-size: 0.85rem; color: #4B5563; padding-left: 1.1rem; margin: 0;">
                        <li>Registro íntegro de cada pensamiento, herramienta invocada, parámetros de entrada y respuesta.</li>
                        <li>Cálculo de métricas de tokens, coste económico y tiempo de respuesta.</li>
                        <li>Exportación en un solo clic del informe técnico auditable en JSON estándar.</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("#### 📋 Matriz de Cumplimiento Regulatorio:")
        compliance_table = [
            {"Artículo": "Art. 6 & Anexo III", "Control": "Clasificación de Alto Riesgo", "Implementación": "Evaluación asistida de reclamaciones con impacto económico relevante"},
            {"Artículo": "Art. 10", "Control": "Gobernanza de Datos & Privacidad", "Implementación": "Filtro sanitizador de PII previo al envío de prompts a APIs externas"},
            {"Artículo": "Art. 12", "Control": "Registro Automático de Eventos (Logs)", "Implementación": "Trazabilidad completa Thought-Action-Observation y métricas por siniestro"},
            {"Artículo": "Art. 13", "Control": "Transparencia y Explicabilidad", "Implementación": "Fundamentación técnica desglosada con referencias a baremos y cláusulas"},
            {"Artículo": "Art. 14", "Control": "Supervisión Humana Efectiva (HITL)", "Implementación": "Resolución asistida como propuesta con botones de validación y control para el gestor"},
            {"Artículo": "Art. 15", "Control": "Precisión, Robustez y Ciberseguridad", "Implementación": "Cálculos matemáticos deterministas en Python y test suite E2E automatizada"},
        ]
        st.dataframe(compliance_table, use_container_width=True, hide_index=True)
