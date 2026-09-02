---
created: 2026-09-02
updated: 2026-09-02
---

# GuardSeguro AI — Contexto del Proyecto

## Objetivo
Proyecto para la candidatura a Senior AI Engineer (GenAI) en Allianz Spain (CoE Automation & AI).

## Arquitectura y Componentes
1. **Frontend**: Streamlit.
2. **Módulo de Gobernanza / PII**: Detección y enmascaramiento de datos personales previo al LLM.
3. **Agente (LangChain / smolagents)**:
   - Tool de Verificación de Cobertura.
   - Tool de Estimación de Costes de Reparación.
4. **Cumplimiento AI Act**: Panel de justificación y trazabilidad/logs para sistemas de IA.
5. **Modelos y Despliegue**: OpenAI GPT-4o-mini o Hugging Face API; Streamlit Community Cloud / Hugging Face Spaces con variables de entorno seguras.
