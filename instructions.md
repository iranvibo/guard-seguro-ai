Aplicar a un puesto de Senior AI Engineer (Gen AI) en Allianz sin experiencia previa en Python es un desafío importante, ya que la vacante exige un "dominio avanzado de Python y desarrollo de software". Sin embargo, la mejor manera de demostrar tu capacidad de adaptación y aprendizaje rápido es construir y desplegar un proyecto que apunte exactamente a lo que el equipo de Allianz Spain busca en su día a día.
Para impresionar a Allianz, tu proyecto no debe ser una simple aplicación de chat de juguete. Debe reflejar que entiendes los retos reales de la IA en el sector de seguros: sistemas de agentes, IA responsable (Responsible AI), cumplimiento regulatorio (AI Act) y despliegue/operación (LLMOps).
A continuación, te propongo un proyecto de tamaño moderado pero de alto impacto, diseñado específicamente para alinearse con los requisitos de la vacante.
El Proyecto: "GuardSeguro AI" – Agente Evaluador de Siniestros con Filtros de IA Responsable
Este proyecto simula un asistente inteligente para gestores de seguros de Allianz que analiza reclamaciones de siniestros, pero con un enfoque técnico avanzado en gobernanza y arquitectura de agentes.
1. ¿Cómo funciona la aplicación? (El Flujo)
Entrada: El usuario (un gestor) introduce el texto de una reclamación de siniestro (por ejemplo: "El cliente Juan Pérez reporta que un árbol cayó sobre su coche matrícula 1234-ABC debido a la tormenta de ayer").
Filtro de IA Responsable (Gobernanza y Privacidad): Antes de enviar nada a un modelo de lenguaje (LLM), un módulo de Python detecta y enmascara datos sensibles de carácter personal (PII) para garantizar la privacidad y seguridad de los datos.
El Agente de IA: Un agente de Python analiza la reclamación utilizando "herramientas" (tools) predefinidas:
Herramienta de Verificación de Cobertura: Un buscador que simula revisar si las condiciones climáticas o el tipo de daño están cubiertos por la póliza tipo.
Herramienta de Cálculo de Estimación: Una función de Python que calcula un coste estimado de reparación rápido basado en el tipo de daño reportado.
Evaluación de Cumplimiento de Normativa (AI Act): La aplicación incluye un panel que muestra cómo el sistema cumple con los requisitos del reglamento de IA de la UE (AI Act) para sistemas de alto/bajo riesgo.
Salida: Devuelve una propuesta de resolución estructurada y un registro (log) transparente de los pasos que siguió el agente para tomar la decisión.
¿Por qué este proyecto cumple con lo que pide Allianz?
Sistemas basados en agentes y GenAI: Al estructurar el código utilizando herramientas que el LLM decide invocar, demuestras que no solo sabes hacer llamadas a una API, sino que comprendes el desarrollo con frameworks de agentes.
IA Responsable y Regulación (AI Act): La inclusión del módulo de enmascaramiento de datos (privacidad) y la justificación del AI Act demuestra que tienes "conocimiento en gobierno de datos y modelos de Responsible AI", un punto clave explícito en la oferta.
LLMOps y Producción: Al desplegar la web app de forma pública, con variables de entorno protegidas (para las claves de API del LLM) y control de versiones en GitHub, demuestras conceptos básicos de LLMOps y preparación para entornos productivos.
Stack Tecnológico Recomendado (Sencillo de aprender)
Para mantener el proyecto acotado pero profesional, utiliza estas herramientas en Python:
Frontend / Interfaz Web: Streamlit. Te permite crear una aplicación web interactiva en Python con menos de 100 líneas de código, sin necesidad de saber HTML/CSS o JavaScript.
Framework de Agentes: LangChain o smolagents (de Hugging Face). Son ideales para definir agentes y herramientas de manera clara y rápida.
Modelos (LLM): La API de OpenAI (GPT-4o-mini) o modelos gratuitos de Hugging Face a través de su API.
Despliegue (Web App): Streamlit Community Cloud o Hugging Face Spaces. Ambos servicios te permiten desplegar la aplicación directamente desde tu repositorio de GitHub de forma gratuita en 5 minutos.
Cómo enfocarlo en la entrevista frente a Allianz
Si te preguntan por tu experiencia en Python y tus proyectos desplegados, tu narrativa debe ser:
"Aunque mi trayectoria previa no ha sido principalmente en Python, he dedicado los últimos meses a dominarlo de forma práctica. Para demostrarlo, diseñé y desplegué GuardSeguro AI. No quería hacer un proyecto genérico, sino uno que abordara los retos específicos que tiene el CoE de Automatización e IA de Allianz: el diseño de sistemas basados en agentes, el enmascaramiento de datos personales para cumplir con la privacidad y la gobernanza de la IA según el AI Act. Está desplegado públicamente y estructurado con buenas prácticas de configuración y LLMOps."