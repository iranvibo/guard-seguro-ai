# GuardSeguro AI — Especificación Funcional y Arquitectura de Referencia Enterprise

El desarrollo de soluciones de Inteligencia Artificial Generativa en el sector asegurador (Insurtech) exige superar el prototipado básico y abordar los retos críticos de la industria: sistemas basados en agentes autónomos, IA responsable (*Responsible AI*), cumplimiento regulatorio estricto (*EU AI Act*), mitigación de alucinaciones matemáticas y despliegue robusto con LLMOps.

A continuación, se define la especificación técnica de la arquitectura de referencia **GuardSeguro AI**, un sistema de alto impacto para la evaluación asistida de siniestros en entornos corporativos.

---

## El Proyecto: "GuardSeguro AI" – Agente Evaluador de Siniestros con Filtros de IA Responsable

Este proyecto implementa un asistente inteligente para gestores y peritos de seguros que analiza declaraciones de siniestros, fundamentado en una arquitectura modular de agentes y gobernanza corporativa.

### 1. ¿Cómo funciona la aplicación? (El Flujo End-to-End)

1. **Entrada:** El gestor introduce el texto libre de una declaración de siniestro (ejemplo: *"El cliente Juan Pérez reporta que un árbol cayó sobre su coche matrícula 1234-ABC debido a la tormenta de ayer"*).
2. **Filtro de IA Responsable (Gobernanza y Privacidad):** Antes de enviar cualquier información a un modelo de lenguaje (LLM), un interceptor local detecta, enmascara y pseudonimiza datos sensibles de carácter personal (PII: DNI, matrículas, teléfonos, emails, cuentas bancarias IBAN) para garantizar el cumplimiento del RGPD.
3. **El Agente de IA (ReAct & Tool Calling):** Un agente orquestador analiza la reclamación invocando herramientas deterministas especializadas:
   - **Herramienta de Verificación de Cobertura (`check_policy_coverage`):** Consulta el catálogo oficial de condiciones de póliza (Auto y Hogar) y exclusiones contractuales aplicando poda inmediata (*short-circuiting*) ante daños no cubiertos.
   - **Herramienta de Evaluación de Riesgo y Fraude (`assess_claim_risk_and_dispute`):** Evalúa inconsistencias o factores de litigio para derivación a peritaje físico presencial.
   - **Herramienta de Cálculo de Estimación (`calculate_repair_estimate`):** Motor matemático determinista que aplica los baremos técnicos por zona dañada y gravedad, deduciendo la franquicia contratada (eliminando alucinaciones numéricas).
4. **Evaluación de Cumplimiento Regulatorio (EU AI Act):** Genera una auditoría automatizada que clasifica el sistema bajo el Anexo III (Sistemas de Alto Riesgo), validando supervisión humana obligatoria (*Human-in-the-Loop*), transparencia y explicabilidad.
5. **Salida:** Emite una propuesta de resolución fuertemente tipada con Pydantic v2, desglose económico exacto y trazabilidad transparente de pasos (*Thought/Action/Observation*).

---

## 2. Capacidades Enterprise Demostradas por el Proyecto

- **Sistemas Basados en Agentes y GenAI:** Diseño de flujos ReAct donde el modelo no responde directamente con texto libre, sino que razona y orquesta llamadas a herramientas deterministas mediante contratos de datos estandarizados.
- **IA Responsable y Regulación (EU AI Act):** Módulo nativo de enmascaramiento reversible de PII y certificación automática de gobernanza según el Reglamento UE 2024/1689.
- **LLMOps y Producción:** Contenerización con Docker multi-stage optimizado y no-root, gestión segura de secretos por entorno, observabilidad de tokens/costes y suite exhaustiva de tests automatizados (198 tests con 100% de éxito).

---

## 3. Stack Tecnológico de Referencia

- **Frontend / Interfaz:** Streamlit con componentes modulares y diseño enterprise.
- **Framework de Agentes:** LangChain con patrones ReAct y fallback determinista offline.
- **Modelos (LLM):** OpenAI (GPT-4o-mini) o Hugging Face API con ejecución resiliente.
- **Contratos de Datos:** Pydantic v2 con validación matemática estricta.
- **Contenerización y Despliegue:** Docker, Docker Compose, Streamlit Community Cloud y Hugging Face Spaces.

---

## 4. Narrativa de Arquitectura Técnica

*"GuardSeguro AI fue diseñado como una arquitectura de referencia para resolver los retos reales de la IA en seguros: el desacoplamiento de la lógica de razonamiento del cálculo matemático, la anonimización local de datos personales antes de invocar APIs externas y la auditoría automática según el EU AI Act. Está preparado para producción con observabilidad, contenerización segura y cobertura total de tests."*