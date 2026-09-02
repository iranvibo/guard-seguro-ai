---
created: 2026-09-02
updated: 2026-09-02
---

# GuardSeguro AI — Contexto del Proyecto y Referencias

## Documentos Fuente de Referencia
- [US.md](file:///Users/bdado/VSCode/allianz-python/US.md): Backlog completo de User Stories estructuradas por épicas y criterios de aceptación (DoD).
- [instructions.md](file:///Users/bdado/VSCode/allianz-python/instructions.md): Especificación funcional, arquitectura del flujo de GuardSeguro AI, stack tecnológico y narrativa para la entrevista.
- [vacancy.md](file:///Users/bdado/VSCode/allianz-python/vacancy.md): Vacante oficial de Allianz Spain (Senior AI Engineer - GenAI, Ref 102972, CoE Automation & AI).

---

## 1. Alineación con la Vacante ([vacancy.md](file:///Users/bdado/VSCode/allianz-python/vacancy.md))
- **Puesto**: Senior AI Engineer (GenAI) — CoE Automation & AI, Allianz Spain.
- **Requisitos clave a demostrar**:
  - Dominio práctico de Python y desarrollo de software.
  - Diseño y construcción de sistemas basados en agentes (Agentic AI) y GenAI.
  - Framework corporativo, gobernanza de datos y principios de **Responsible AI**.
  - Cumplimiento de normativas regulatorias (**EU AI Act**).
  - Entornos cloud y buenas prácticas de **LLMOps** / MLOps para producción.

---

## 2. Especificación del Proyecto: "GuardSeguro AI" ([instructions.md](file:///Users/bdado/VSCode/allianz-python/instructions.md))
Agente evaluador de siniestros de seguros con filtros de gobernanza e IA responsable.

### Flujo de la Aplicación:
1. **Entrada**: Texto de reclamación de siniestro introducido por el gestor.
2. **Filtro de IA Responsable (Privacidad / PII)**: Detección y anonimización/enmascaramiento de datos personales sensibles antes de la llamada a cualquier LLM.
3. **Agente de IA (Tool Calling)**:
   - *Herramienta de Verificación de Cobertura*: Comprueba si las condiciones o daños están cubiertos por póliza tipo.
   - *Herramienta de Cálculo de Estimación*: Función Python para calcular coste estimado de reparación según el tipo de daño.
4. **Evaluación de Cumplimiento Normativo (EU AI Act)**: Panel de auditoría/cumplimiento para clasificar el sistema según riesgo y requisitos del AI Act.
5. **Salida y Trazabilidad**: Propuesta de resolución estructurada y registro transparente (logs/traces) del razonamiento del agente.

### Stack Tecnológico:
- **UI / Frontend**: Streamlit.
- **Agentes**: LangChain o smolagents.
- **Modelos (LLM)**: OpenAI API (`gpt-4o-mini`) o Hugging Face API.
- **Contenerización y Entorno**: Docker (`Dockerfile` optimizado y seguro) y `docker-compose.yml` para reproducibilidad y aislamiento.
- **Despliegue y LLMOps**: Streamlit Community Cloud / Hugging Face Spaces / Contenedores Cloud con variables de entorno protegidas (`.env` / secrets) y control de versiones en GitHub.

---

## 3. Estado de Implementación
- **US-01 (Cimientos & Docker)**: ✅ Completada. Estructura modular `src/` (`core`, `privacy`, `tools`, `agent`, `compliance`), `Dockerfile` no-root con Python 3.11-slim, `docker-compose.yml`, `requirements.txt`, `.env.example`, `.dockerignore`, `.gitignore` y `src/core/config.py` con validación de entorno.
- **US-02 (Modelos de Datos & Estructuras Base)**: ✅ Completada. Esquemas fuertemente tipados en Pydantic v2 en `src/core/models.py` (`ClaimInput`, `AnonymizedClaim`, `CoverageStatus`, `DamageSeverity`, `CoverageCheckResult`, `CostBreakdown`, `ClaimAssessment`), reexportados en `src/core/__init__.py`, suite de tests unitarios en `tests/test_models.py` con 100% de tests pasando en Docker.
- **US-03 (Módulo de Detección y Enmascaramiento PII)**: ✅ Completada. Motor de IA Responsable y privacidad RGPD en `src/privacy/patterns.py` y `src/privacy/masker.py`. Detección regex y gazetteer contextual de DNI/NIE españoles, matrículas (actuales y provinciales), teléfonos (móviles/fijos con prefijo +34/0034), emails, cuentas bancarias IBAN, direcciones postales y nombres propios. Implementadas funciones reversibles `mask_pii(text)`, `unmask_pii(text, pii_mapping)` y puente `anonymize_claim(claim_input)`. Suite de 35 tests unitarios con 5 casos reales de siniestros pasando al 100% en Docker.
- **US-04 (Herramienta de Verificación de Coberturas)**: ✅ Completada. Catálogo JSON oficial en `src/tools/data/policy_catalog.json` con coberturas estándar (rotura de lunas, granizo, colisión, robo, vandalismo, asistencia, agua, incendio, RC) y exclusiones explícitas (desgaste, alcohol, dolo). Lógica de inferencia y normalización en `src/tools/policy_coverage.py`, función `verify_policy_coverage` y `@tool` de LangChain `check_policy_coverage`. Suite de 29 nuevos tests en `tests/test_tools_coverage.py` (64 tests totales en verde en Docker).
- **US-05 (Herramienta de Estimación Económica y Baremos de Reparación)**: ✅ Completada. Catálogo técnico de baremos en `src/tools/data/repair_rates.json` con costes de materiales y mano de obra para zonas clave (chapa, pintura, luna delantera, parachoques, motor, retrovisor, faros, cerradura, fontanería) en 3 niveles de severidad (Leve, Moderado, Grave). Módulo de cálculo determinista en `src/tools/repair_calculator.py` con `compute_repair_estimate` y `@tool` de LangChain `calculate_repair_estimate`. Deducción exacta de franquicia (`Coste Neto = max(0, Coste Bruto - Franquicia)`). Suite de 49 nuevos tests en `tests/test_tools_calculator.py` (113 tests totales en verde en Docker).
- **US-06 (Agente ReAct con Tool Calling)**: ✅ Completada. Implementado agente ReAct en `src/agent/claim_agent.py`, templates de prompts con rol explícito de Allianz Spain en `src/agent/prompts.py`, y parser de salida estructurada con extracción JSON/Pydantic en `src/agent/parser.py`. El agente orquesta `check_policy_coverage` y `calculate_repair_estimate` para generar un `ClaimAssessment` fuertemente tipado. Incluye pipeline determinista para ejecución offline/testing sin consumo de tokens externos. Suite de 21 tests unitarios en `tests/test_agent.py` (134 tests totales en verde en Docker).
- **US-07 (Trazabilidad, Observabilidad y Registro de Razonamiento)**: ✅ Completada. Creados esquemas `ExecutionMetrics` y `ToolCallTrace` en `src/core/models.py`. Implementado módulo de observabilidad en `src/agent/observability.py` con `AgentAuditorCallbackHandler` para captura de eventos LangChain, métricas de latencia de ejecución (`execution_time_seconds`), conteo y estimación de tokens (`prompt_tokens`, `completion_tokens`, `total_tokens`), estimación de costes en USD, formateadores visuales de auditoría en Markdown (`format_audit_log_markdown`), diagramas de flujo Mermaid (`format_reasoning_flow_mermaid`) y exportación a diccionario JSON (`export_audit_trail_dict`). Integrado en `ClaimEvaluatorAgent` y suite de 14 tests en `tests/test_observability.py` (148 tests totales en verde en Docker).
- **US-08 (Ficha de Auditoría y Cumplimiento EU AI Act)**: ✅ Completada. Creado módulo de gobernanza y auditoría regulatoria en `src/compliance/models.py` y `src/compliance/auditor.py`. Modelos Pydantic v2 `EUAIActComplianceReport`, `RiskClassification` (categorización como Alto Riesgo bajo Anexo III Punto 5a del Reglamento UE 2024/1689), `HumanInTheLoopAudit` (garantía de propuesta asistida y supervisión humana bajo Art. 14), `TransparencyAudit` (verificación de registros y explicabilidad bajo Art. 12 y 13 con logs de US-07), `DataPrivacyAudit` (acreditación de minimización y filtro PII bajo Art. 10 y RGPD). Formateador ejecutivo en Markdown (`format_compliance_report_markdown`), serializador JSON (`export_compliance_report_dict`), motor `generate_compliance_report`, e integración `evaluate_claim_with_compliance`. Suite de 15 tests unitarios en `tests/test_compliance.py` (163 tests totales en verde en Docker).
- **US-09 (Dashboard Interactivo en Streamlit)**: ✅ Completada. Implementada interfaz web interactiva en `app.py` y `src/ui/` (`sample_cases.py`, `components.py`). Selector de 3 casos de prueba predefinidos en 1 clic (Tormenta aprobada, Desgaste excluido, Accidente complejo con terceros) más texto libre. Vista estructurada en 3 paneles: 1. Privacidad (comparador antes/después del enmascaramiento PII y tabla de tokens), 2. Resolución (tarjeta con dictamen, métricas financieras de materiales/mano de obra/franquicia/neto, fundamentación técnica y botones Human-in-the-Loop), 3. Trazabilidad y AI Act (pestañas con árbol de razonamiento/pasos intermedios/latencia/tokens, ficha regulatoria del EU AI Act con tabla de controles y botones de descarga JSON/Markdown). Suite de 6 nuevos tests en `tests/test_ui_cases.py` (169 tests totales en verde en Docker).
- **US-10 (Contenerización Docker, Despliegue Cloud & LLMOps)**: ✅ Completada. Corregido `.dockerignore` para permitir tests y contexto completo de compilación. Imagen Docker multi-stage (`python:3.11-slim`, usuario no-root `appuser:1001`, healthcheck HTTP) validada localmente con `docker compose up --build` y 169 tests pasando al 100% en el contenedor (`docker compose run --rm --entrypoint pytest guardseguro-ai`). Documentación profesional de primer nivel en `README.md` con arquitectura, diagramas Mermaid, guías paso a paso de despliegue en Streamlit Community Cloud, Hugging Face Spaces y Docker, matriz regulatoria del EU AI Act y justificación técnica para la vacante Senior AI Engineer de Allianz Spain. Backlog de User Stories completado al 100%.
- **Separación Estricta de Modos de Ejecución (OpenAI vs Determinista)**: En `src/agent/claim_agent.py` y `app.py`, se eliminó el fallback automático a evaluación determinista cuando el usuario tiene seleccionado el modo "OpenAI GPT-4o-mini". Si la API de OpenAI responde con error (ej. 401 Unauthorized, 429 RateLimit) o falta la clave, el sistema lanza la excepción correspondiente y la interfaz muestra únicamente el panel de error detallado, sin generar ni mostrar evaluaciones ficticias o no solicitadas del motor determinista. El motor determinista solo se ejecuta cuando el usuario selecciona explícitamente el modo "Deterministic Engine (Offline / Alta Fidelidad)". Suite de 171 tests en verde en Docker (`docker compose run --rm --entrypoint pytest guardseguro-ai`).
- **Casos de Prueba Realistas Auto vs Hogar & Validación de Coherencia de Ramo**: Se incorporó un catálogo ampliado de casos de prueba reales en `src/ui/sample_cases.py` cubriendo tanto **Auto** (tormenta/granizo, desgaste mecánico, colisión múltiple) como **Hogar** (tormenta con rotura de ventanales climalit/claraboyas, fuga de agua con daños a paramentos y vecinos, exclusión por falta de mantenimiento en cubierta). En `src/tools/data/policy_catalog.json` y `src/tools/data/repair_rates.json` se añadieron garantías específicas para cristalería de hogar (`rotura_cristales_hogar`, `cristaleria_hogar`), albañilería/pintura (`albanileria_pintura_hogar`), y exclusiones cruzadas de coherencia de riesgo (`vehiculos_en_hogar` e `inmuebles_en_auto`) para evitar que daños de automóviles sean indebidamente aprobados bajo pólizas residenciales. En `app.py`, la selección de casos sincroniza automáticamente el tipo de póliza correspondiente. Suite de 177 tests pasando al 100% en Docker.
- **Botón de Copia de Informe en JSON al Portapapeles ('Copy inform in JSON')**: Se implementó en `src/ui/components.py` la función `build_claim_report_json` y el componente visual `render_report_header_with_copy_button` al inicio del panel de resultados en `app.py`. Este botón copia al portapapeles un JSON exhaustivo con: `caso_cobertura` (estado, dictamen, franquicia, totales y desglose financiero), `tipo_poliza`, `descripcion` (texto original, sanitizado y recuento de PII) y `comportamiento_agente` (herramientas ejecutadas, métricas y detalle de qué envió (`enviado`), qué recibió (`recibido`) y el pensamiento (`pensamiento`) en cada paso intermedio). Integrado con API Clipboard del navegador y fallback a `execCommand`. Suite de 180 tests unitarios en verde en Docker (`docker compose run --rm --entrypoint pytest guardseguro-ai`).
