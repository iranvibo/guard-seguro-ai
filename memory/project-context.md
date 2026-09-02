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

