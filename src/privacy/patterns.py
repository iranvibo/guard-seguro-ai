"""Regular expressions and gazetteers for Spanish PII detection in insurance claims.

Covers DNI/NIE, license plates (modern & provincial), phone numbers,
emails, IBANs, physical addresses, and Spanish person names.
"""

import re
from typing import Set

# ---------------------------------------------------------------------------
# Spanish First Names & Surnames Gazetteer
# ---------------------------------------------------------------------------

COMMON_SPANISH_FIRST_NAMES: Set[str] = {
    "juan", "pedro", "carlos", "josé", "jose", "manuel", "antonio", "francisco",
    "david", "javier", "daniel", "alejandro", "miguel", "álvaro", "alvaro",
    "sergio", "jorge", "pablo", "fernando", "luis", "alberto", "raúl", "raul",
    "maría", "maria", "carmen", "ana", "laura", "marta", "elena", "lucía", "lucia",
    "cristina", "paula", "sara", "claudia", "alicia", "raquel", "patricia",
    "rosa", "pilar", "mercedes", "isabel", "beatriz", "silvia", "nuria", "inés", "ines",
    "mónica", "monica", "teresa", "irene", "rocío", "rocio", "ángela", "angela",
    "marina", "natalia", "eva", "victoria", "julia", "sonia", "lorena", "noelia",
    "guillermo", "hugo", "adrian", "adrián", "diego", "mario", "víctor", "victor",
    "rodrigo", "marcos", "gonzalo", "ignacio", "joaquín", "joaquin", "andrés", "andres",
    "rubén", "ruben", "gabriel", "emilio", "rafael", "borja", "guillem", "jordi",
    "montserrat", "dolores", "concepción", "amparo", "gema", "gemma", "estefanía", "estefania"
}

COMMON_SPANISH_SURNAMES: Set[str] = {
    "garcía", "garcia", "gonzález", "gonzalez", "rodríguez", "rodriguez",
    "fernández", "fernandez", "lópez", "lopez", "martínez", "martinez",
    "sánchez", "sanchez", "pérez", "perez", "gómez", "gomez", "martín", "martin",
    "jiménez", "jimenez", "ruiz", "hernández", "hernandez", "díaz", "diaz",
    "moreno", "álvarez", "alvarez", "romero", "alonso", "gutiérrez", "gutierrez",
    "navarro", "torres", "domínguez", "dominguez", "vázquez", "vazquez",
    "ramos", "gil", "ramírez", "ramirez", "serrano", "blanco", "molina",
    "morales", "suárez", "suarez", "ortega", "delgado", "castro", "ortiz",
    "marín", "marin", "rubio", "núñez", "nuñez", "medina", "iglesias", "castillo",
    "cortés", "cortes", "garrido", "santos", "lozano", "guerrero", "cano",
    "prieto", "méndez", "mendez", "calvo", "cruz", "gallego", "vidal", "león", "leon",
    "marquez", "márquez", "herrera", "peña", "flores", "cabrera", "campos", "vega",
    "fuentes", "carrasco", "díez", "diez", "caballero", "reyes", "nieto", "aguilar",
    "pascual", "santana", "herrero", "lorenzo", "montero", "hidalgo", "giménez", "gimenez",
    "ibáñez", "ibañez", "ferrari", "dado", "velasco", "soler", "esteban", "parra"
}

# ---------------------------------------------------------------------------
# Regex Patterns
# ---------------------------------------------------------------------------

# DNI & NIE (Spanish national identity cards)
# e.g., 12345678Z, 12.345.678-A, 12345678-A, X1234567A, Y-1234567-B, Z.1234567.C
PATTERN_DNI_NIE = re.compile(
    r"\b(?:[XYZxyz][\s\.\-]?)?\d{1,2}(?:[\s\.\-]?\d{3}){2}[\s\.\-]?[A-HJ-NP-TV-Za-hj-np-tv-z]\b"
)

# Spanish License Plates (Matrículas)
# Modern: 4 digits + 3 letters (e.g., 1234-ABC, 1234 ABC, 1234BCD, 9988-BZX)
# Classic provincial: 1-2 provincial letters + 4 digits + 1-2 letters (e.g., M-1234-AB, B-5678-CD, SE 1234 AB)
PATTERN_MATRICULA = re.compile(
    r"\b(?:\d{4}[-\s]?[A-Za-z]{3}|[A-Za-z]{1,2}[-\s]?\d{4}[-\s]?[A-Za-z]{1,2})\b"
)

# Spanish Phone Numbers (Mobiles 6xx, 7xx; Landlines 8xx, 9xx; optional +34 or 0034)
# Formats: +34 612 345 678, +34 91 123 45 67, 612345678, +34 688 99 00 11, 912345678
PATTERN_TELEFONO = re.compile(
    r"(?:(?:\+|00)34[\s\.\-]?)?(?:[6789](?:[\s\.\-]?\d){8})\b"
)

# Email addresses
PATTERN_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# IBAN (Spanish 24 chars: ES + 2 check + 20 digits; also European general formats)
# e.g. ES91 2100 0418 4502 0005 1332, ES91-2100-0418-4502-0005-1332, ES9121000418450200051332
PATTERN_IBAN = re.compile(
    r"\b[A-Z]{2}\d{2}(?:[-\s]?\d{4}){5}\b|\b[A-Z]{2}\d{2}(?:[-\s]?\d{2,4}){4,7}\b"
)

# Spanish Postal Addresses (Direcciones)
# e.g., Calle Alcalá 45, Madrid; Avda. Diagonal 450, Barcelona; Calle Gran Vía 28, Madrid; Paseo de la Castellana 200, Madrid
PATTERN_DIRECCION = re.compile(
    r"\b(?:Calle|C\/|Avda\.?|Avenida|Paseo|Plaza|Camino|Carretera|Ctra\.?|Ronda|Travesía|Trav\.?|Gran Vía|Bulevar|Polígono|Urb\.?|Urbanización)"
    r"\s+(?:de\s+la\s+|de\s+|del\s+)?[A-ZÁÉÍÓÚÑa-záéíóúñ0-9\sºª\-]+?"
    r"(?:,\s*(?:nº|n[ºo]|número|\d+)[A-Za-z0-9\sºª\-]*)?"
    r"(?:(?:,\s*|\s+de\s+)(?:\d{5}\s*)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?"
    r"(?=[,;\.\n\(\)]|\s+con\b|\s+conducía\b|\s+solicita\b|\s+declara\b|\s+tras\b|\s+cuando\b|\s+quien\b|\s+donde\b|\s+Se\b|$)",
    re.UNICODE
)

# Contextual Address Detection
# Matches: "con domicilio en Paseo de la Castellana 200, Madrid", "sito en Calle Mayor 10", "residente en Avda. Diagonal 450, Barcelona"
PATTERN_CONTEXTUAL_ADDRESS = re.compile(
    r"\b(?:domicilio(?:\s+en|\s+sito\s+en)?|dirección(?:\s+en)?|sito\s+en|sita\s+en|residente\s+en|residencia\s+en|inmueble\s+sito\s+en|vivienda\s+sita\s+en|ubicado\s+en|ubicada\s+en)[:\s]+"
    r"((?:Calle|C\/|Avda\.?|Avenida|Paseo|Plaza|Camino|Carretera|Ctra\.?|Ronda|Travesía|Trav\.?|Gran Vía|Bulevar|Polígono|Urb\.?|Urbanización)\s+[A-ZÁÉÍÓÚÑa-záéíóúñ0-9\sºª\-]+?(?:(?:,\s*|\s+de\s+)(?:\d{5}\s*)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)"
    r"(?=[,;\.\n\(\)]|\s+conducía\b|\s+cuando\b|\s+solicita\b|\s+declara\b|\s+tras\b|$)",
    re.UNICODE | re.IGNORECASE,
)



# Contextual Prefix Name Detection
# Matches: "El cliente Juan Pérez", "tomador: Carlos Gómez", "conductora María Rodríguez López"
PATTERN_CONTEXTUAL_NAME = re.compile(
    r"\b(?:cliente|tomador|tomadora|conductor|conductora|asegurado|asegurada|perito|afectado|afectada|propietario|propietaria|titular|"
    r"Don|Doña|D\.|Dª\.|Sr\.|Sra\.|Señor|Señora|Sr\./Sra\.)[:\s]+"
    r"((?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de\s+la\s+|de\s+|del\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3}))\b",
    re.UNICODE
)
