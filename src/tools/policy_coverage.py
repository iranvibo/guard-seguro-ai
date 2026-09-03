"""Policy coverage verification tool for GuardSeguro Seguros insurance claims.

Provides deterministic checking of policy terms, coverage conditions, and standard
deductibles against structured policy catalogs for Auto and Hogar lines of business.
"""

import json
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from src.core.models import CoverageCheckResult

logger = logging.getLogger(__name__)

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parent / "data" / "policy_catalog.json"


def _normalize_text(text: str) -> str:
    """Normalize text by lowercasing, removing accents, and stripping non-alphanumeric chars.

    Args:
        text: Raw input string.

    Returns:
        Cleaned, accent-free lowercase string.
    """
    if not text:
        return ""
    # Normalize unicode characters to decompose accents (NFD)
    nfkd_form = unicodedata.normalize("NFKD", text)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Convert to lowercase and replace punctuation with single spaces
    normalized = re.sub(r"[^\w\s]", " ", only_ascii.lower())
    return re.sub(r"\s+", " ", normalized).strip()


@lru_cache(maxsize=4)
def load_policy_catalog(catalog_path: Optional[str] = None) -> Dict[str, Any]:
    """Load policy coverage catalog from JSON file with caching.

    Args:
        catalog_path: Optional custom path to JSON catalog file.

    Returns:
        Dictionary containing policy_categories, policy_exclusions, and defaults.
    """
    path = Path(catalog_path) if catalog_path else DEFAULT_CATALOG_PATH
    try:
        with open(path, mode="r", encoding="utf-8") as f:
            catalog = json.load(f)
            logger.info("Policy catalog loaded successfully from %s", path)
            return catalog
    except Exception as exc:
        logger.error("Failed to load policy catalog from %s: %s. Using fallback.", path, exc)
        return {
            "policy_categories": [],
            "policy_exclusions": [],
            "default_unknown_response": {
                "is_covered": False,
                "coverage_type": "Requiere Peritaje / No Catalogado",
                "standard_deductible": 0.0,
                "conditions": "Error al cargar catálogo de coberturas. Requiere revisión pericial.",
            },
        }


def _match_keywords(normalized_text: str, keywords: List[str]) -> int:
    """Count how many keywords or key phrases match the input text."""
    score = 0
    for kw in keywords:
        norm_kw = _normalize_text(kw)
        if not norm_kw:
            continue
        # Exact word/phrase boundary or substring match for phrases
        if " " in norm_kw:
            if norm_kw in normalized_text:
                score += 3  # Higher weight for multi-word exact match
        else:
            pattern = rf"\b{re.escape(norm_kw)}\b"
            if re.search(pattern, normalized_text):
                score += 2
            elif norm_kw in normalized_text:
                score += 1
    return score


def verify_policy_coverage(
    damage_type: str,
    policy_type: str = "Auto",
    catalog: Optional[Dict[str, Any]] = None,
) -> CoverageCheckResult:
    """Evaluate whether a reported damage or incident type is covered under GuardSeguro policies.

    Args:
        damage_type: Description or category of the incident/damage reported.
        policy_type: Type of policy (e.g. 'Auto', 'Hogar'). Defaults to 'Auto'.
        catalog: Optional in-memory catalog dictionary.

    Returns:
        Structured CoverageCheckResult object with coverage status, conditions, and deductible.
    """
    if catalog is None:
        catalog = load_policy_catalog()

    norm_input = _normalize_text(damage_type)
    if not norm_input:
        return CoverageCheckResult(
            is_covered=False,
            coverage_type="Indeterminado",
            conditions="No se proporcionó descripción del tipo de daño o siniestro.",
            standard_deductible=0.0,
        )

    # 1. Check explicit exclusions first (e.g., alcohol, natural wear, intentional fraud)
    exclusions = catalog.get("policy_exclusions", [])
    for exclusion in exclusions:
        allowed_policies = exclusion.get("policy_types", ["Auto", "Hogar"])
        if policy_type not in allowed_policies:
            continue
        score = _match_keywords(norm_input, exclusion.get("keywords", []))
        if score > 0:
            return CoverageCheckResult(
                is_covered=False,
                coverage_type=f"Exclusión: {exclusion.get('name', 'No Cubierto')}",
                conditions=exclusion.get(
                    "conditions",
                    "Siniestro expresamente excluido según el condicionado general de la póliza.",
                ),
                standard_deductible=0.0,
            )

    # 2. Check covered policy categories and pick best match
    categories = catalog.get("policy_categories", [])
    best_category = None
    best_score = 0

    for cat in categories:
        allowed_policies = cat.get("policy_types", ["Auto", "Hogar"])
        if policy_type not in allowed_policies:
            continue
        score = _match_keywords(norm_input, cat.get("keywords", []))
        if score > best_score:
            best_score = score
            best_category = cat

    # 3. If a clear covered category was matched with positive score
    if best_category is not None and best_score > 0:
        return CoverageCheckResult(
            is_covered=best_category.get("is_covered", True),
            coverage_type=best_category.get("name", "Cobertura Estándar"),
            conditions=best_category.get("conditions", "Cobertura estándar aplicable."),
            standard_deductible=float(best_category.get("standard_deductible", 0.0)),
        )

    # 4. Handle ambiguous / uncatalogued cases requiring expert appraisal
    default_resp = catalog.get(
        "default_unknown_response",
        {
            "is_covered": False,
            "coverage_type": "Requiere Peritaje / No Catalogado",
            "standard_deductible": 0.0,
            "conditions": "El tipo de siniestro no se encuentra tipificado en el catálogo automático. Requiere revisión pericial.",
        },
    )

    return CoverageCheckResult(
        is_covered=default_resp.get("is_covered", False),
        coverage_type=default_resp.get("coverage_type", "Requiere Peritaje / No Catalogado"),
        conditions=default_resp.get("conditions", "Requiere revisión pericial humana."),
        standard_deductible=float(default_resp.get("standard_deductible", 0.0)),
    )


@tool
def check_policy_coverage(damage_type: str, policy_type: str = "Auto") -> str:
    """Verifica si un tipo de siniestro o daño específico tiene cobertura en la póliza de GuardSeguro.

    Utiliza el catálogo oficial de coberturas y exclusiones de GuardSeguro Seguros para determinar
    si el incidente (ej. rotura de lunas, granizo, colisión, robo, vandalismo, etc.) está cubierto,
    junto con sus condiciones aplicables y la franquicia estándar correspondiente.

    Args:
        damage_type: Descripción o categoría del daño (ej. 'rotura de parabrisas', 'granizo en techo', 'golpe trasero', 'robo').
        policy_type: Tipo de póliza a consultar ('Auto' o 'Hogar'). Por defecto 'Auto'.

    Returns:
        JSON estructurado con campos:
        - cubierto (bool): True si el siniestro está cubierto por la póliza.
        - condiciones (str): Términos, cláusulas y condiciones aplicables.
        - franquicia_estandar (float): Franquicia a aplicar en euros (€).
        - tipo_cobertura (str): Nombre de la cobertura identificada o motivo de exclusión.
        - is_covered (bool): Alias en inglés para compatibilidad.
        - coverage_type (str): Alias en inglés para compatibilidad.
        - standard_deductible (float): Alias en inglés para compatibilidad.
    """
    result = verify_policy_coverage(damage_type=damage_type, policy_type=policy_type)

    payload = {
        "cubierto": result.is_covered,
        "condiciones": result.conditions,
        "franquicia_estandar": result.standard_deductible,
        "tipo_cobertura": result.coverage_type,
        "is_covered": result.is_covered,
        "conditions": result.conditions,
        "coverage_type": result.coverage_type,
        "standard_deductible": result.standard_deductible,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
