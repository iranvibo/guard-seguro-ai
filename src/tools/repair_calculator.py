"""Repair cost estimation and baremo calculation tool for GuardSeguro Seguros.

Provides deterministic calculation of material and labor costs based on damaged
vehicle/property zones and severity levels, subtracting deductibles to compute
the net claim settlement amount.
"""

import json
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from langchain_core.tools import tool

from src.core.models import CostBreakdown, DamageSeverity

logger = logging.getLogger(__name__)

DEFAULT_RATES_PATH = Path(__file__).resolve().parent / "data" / "repair_rates.json"

SEVERITY_MAP = {
    "leve": "Leve",
    "light": "Leve",
    "baja": "Leve",
    "low": "Leve",
    "1": "Leve",
    "moderado": "Moderado",
    "moderada": "Moderado",
    "moderate": "Moderado",
    "medio": "Moderado",
    "media": "Moderado",
    "medium": "Moderado",
    "2": "Moderado",
    "grave": "Grave",
    "severo": "Grave",
    "severa": "Grave",
    "severe": "Grave",
    "alta": "Grave",
    "high": "Grave",
    "3": "Grave",
}


def _normalize_text(text: str) -> str:
    """Normalize text by lowercasing, removing accents and stripping punctuation."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    only_ascii = "".join([c for c in nfkd if not unicodedata.combining(c)])
    clean = re.sub(r"[^\w\s]", " ", only_ascii.lower())
    return re.sub(r"\s+", " ", clean).strip()


def normalize_severity(severity: Union[str, DamageSeverity]) -> str:
    """Normalize severity input to standard 'Leve', 'Moderado', or 'Grave'.

    Args:
        severity: String or DamageSeverity enum.

    Returns:
        Standardized severity string ('Leve', 'Moderado', 'Grave').
    """
    if isinstance(severity, DamageSeverity):
        return severity.value

    clean = _normalize_text(str(severity))
    return SEVERITY_MAP.get(clean, "Moderado")


@lru_cache(maxsize=4)
def load_repair_rates(rates_path: Optional[str] = None) -> Dict[str, Any]:
    """Load repair rates and baremos catalog from JSON with caching.

    Args:
        rates_path: Optional custom path to JSON rates file.

    Returns:
        Dictionary containing zones, severities, and rates.
    """
    path = Path(rates_path) if rates_path else DEFAULT_RATES_PATH
    try:
        with open(path, mode="r", encoding="utf-8") as f:
            rates = json.load(f)
            logger.info("Repair rates loaded successfully from %s", path)
            return rates
    except Exception as exc:
        logger.error("Failed to load repair rates from %s: %s. Using in-memory fallback.", path, exc)
        return {
            "currency": "EUR",
            "zones": {
                "chapa": {
                    "name": "Chapa / Carrocería",
                    "aliases": ["chapa", "carroceria", "capo", "techo", "puerta"],
                    "severities": {
                        "Leve": {"materials": 45.0, "labor": 110.0, "description": "Desabollado leve."},
                        "Moderado": {"materials": 160.0, "labor": 275.0, "description": "Reparación de chapa media."},
                        "Grave": {"materials": 480.0, "labor": 550.0, "description": "Sustitución de pieza de chapa."},
                    },
                }
            },
            "default_fallback": {
                "zone": "chapa",
                "severity": "Moderado",
                "materials": 150.0,
                "labor": 200.0,
                "description": "Estimación baremada estándar fallback.",
            },
        }


def _find_best_matching_zone(
    damaged_zone_input: str,
    zones_catalog: Dict[str, Any],
    policy_type: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Identify the catalog zone that best matches the user's damaged zone description.

    Takes into account the policy_type (Auto vs Hogar) to prioritize branch-coherent baremos.
    """
    norm_input = _normalize_text(damaged_zone_input)
    norm_policy = _normalize_text(policy_type) if policy_type else ""

    # Filter/categorize by policy type if provided
    valid_zones = zones_catalog
    if norm_policy:
        branch_name = "Hogar" if "hogar" in norm_policy or "home" in norm_policy else "Auto"
        # Preference dictionary for matching
    else:
        branch_name = None

    if not norm_input:
        default_key = "albanileria_pintura_hogar" if branch_name == "Hogar" else "chapa"
        return default_key, zones_catalog.get(default_key, {})

    # 1. Exact zone key match
    if norm_input in zones_catalog:
        matched_data = zones_catalog[norm_input]
        zone_policies = matched_data.get("policy_types", ["Auto", "Hogar"])
        if not branch_name or branch_name in zone_policies:
            return norm_input, matched_data

    best_zone_key = None
    best_score = 0

    for zone_key, zone_data in zones_catalog.items():
        zone_policies = zone_data.get("policy_types", ["Auto", "Hogar"])
        policy_multiplier = 1.0
        if branch_name:
            if branch_name in zone_policies:
                policy_multiplier = 2.0
            else:
                policy_multiplier = 0.5

        aliases = zone_data.get("aliases", [zone_key])
        for alias in aliases:
            norm_alias = _normalize_text(alias)
            if not norm_alias:
                continue

            base_score = 0
            # Multi-word exact match gets highest score
            if " " in norm_alias and norm_alias in norm_input:
                base_score = 10 + len(norm_alias)
            elif norm_alias == norm_input:
                base_score = 8 + len(norm_alias)
            elif re.search(rf"\b{re.escape(norm_alias)}\b", norm_input):
                base_score = 5 + len(norm_alias)
            elif norm_alias in norm_input or norm_input in norm_alias:
                base_score = 2 + len(norm_alias)

            score = base_score * policy_multiplier
            if score > best_score:
                best_score = score
                best_zone_key = zone_key

    if best_zone_key and best_score > 0:
        return best_zone_key, zones_catalog[best_zone_key]

    # Default fallback if no keyword matches
    default_key = "albanileria_pintura_hogar" if branch_name == "Hogar" else "chapa"
    if default_key not in zones_catalog:
        default_key = list(zones_catalog.keys())[0] if zones_catalog else "chapa"
    return default_key, zones_catalog.get(default_key, {})


def compute_repair_estimate(
    damaged_zone: str,
    severity: Union[str, DamageSeverity] = DamageSeverity.LIGHT,
    deductible: float = 0.0,
    rates: Optional[Dict[str, Any]] = None,
    policy_type: Optional[str] = None,
) -> Tuple[CostBreakdown, Dict[str, Any]]:
    """Compute exact repair cost estimation based on damaged zone and severity baremos.

    Formula:
        Gross Total = Materials + Labor
        Net Payout = max(0.0, Gross Total - Deductible)

    Args:
        damaged_zone: Affected part or area (e.g., 'chapa', 'pintura', 'luna delantera', 'parachoques', 'motor', 'fontaneria', 'albanileria_pintura_hogar').
        severity: Damage severity ('Leve', 'Moderado', 'Grave').
        deductible: Policy deductible to subtract in EUR (€).
        rates: Optional preloaded rates catalog.
        policy_type: Optional policy type ('Auto', 'Hogar') to select branch-specific baremos.

    Returns:
        Tuple containing:
        - CostBreakdown: Pydantic model with materials, labor, gross_total, deductible, net_total.
        - Dict: Metadata containing zone_name, standardized_severity, description, and raw details.
    """
    if rates is None:
        rates = load_repair_rates()

    zones_catalog = rates.get("zones", {})
    zone_key, zone_data = _find_best_matching_zone(damaged_zone, zones_catalog, policy_type=policy_type)
    std_severity = normalize_severity(severity)

    severities_data = zone_data.get("severities", {})
    severity_info = severities_data.get(
        std_severity,
        severities_data.get("Moderado", rates.get("default_fallback", {})),
    )

    materials = float(severity_info.get("materials", 100.0))
    labor = float(severity_info.get("labor", 150.0))
    deductible_val = max(0.0, float(deductible))

    breakdown = CostBreakdown(
        materials=round(materials, 2),
        labor=round(labor, 2),
        deductible=round(deductible_val, 2),
    )

    metadata = {
        "zone_key": zone_key,
        "zone_name": zone_data.get("name", zone_key.capitalize()),
        "severity": std_severity,
        "description": severity_info.get("description", "Reparación baremada estándar."),
        "estimated_hours": severity_info.get("estimated_hours", 0.0),
        "currency": rates.get("currency", "EUR"),
    }

    return breakdown, metadata


@tool
def calculate_repair_estimate(
    damaged_zone: str,
    severity: str = "Leve",
    deductible: float = 0.0,
    policy_type: str = "Auto",
) -> str:
    """Calcula la estimación económica exacta de reparación según la zona dañada, la gravedad y el ramo de la póliza.

    Aplica los baremos técnicos de GuardSeguro Seguros para obtener el desglose matemático:
    Coste Bruto = Materiales + Mano de Obra
    Coste Neto (Total a Pagar) = max(0, Coste Bruto - Franquicia)

    Args:
        damaged_zone: Zona o elemento dañado (ej. Auto: 'chapa', 'pintura', 'luna delantera', 'parachoques', 'motor', 'retrovisor', 'faros', 'cerradura'; Hogar: 'fontaneria', 'cristaleria_hogar', 'albanileria_pintura_hogar', 'tejado', 'cubierta').
        severity: Nivel de gravedad del daño ('Leve', 'Moderado', 'Grave'). Por defecto 'Leve'.
        deductible: Franquicia aplicable en euros (€). Por defecto 0.0.
        policy_type: Tipo de póliza ('Auto' u 'Hogar'). Asegura que se apliquen baremos coherentes con el ramo asegurado. Por defecto 'Auto'.

    Returns:
        JSON estructurado con el desglose numérico exacto:
        - materiales (float): Coste de materiales y recambios en EUR (€).
        - mano_de_obra (float): Coste de mano de obra en EUR (€).
        - coste_bruto (float): Suma exacta de materiales + mano de obra (€).
        - franquicia (float): Franquicia aplicada y deducida (€).
        - total_a_pagar (float): Importe neto a indemnizar por la aseguradora (€).
        - zona_afectada (str): Nombre de la zona baremada.
        - gravedad (str): Nivel de gravedad ('Leve', 'Moderado', 'Grave').
        - detalle (str): Descripción técnica de la intervención.
        - horas_estimadas (float): Tiempo estimado de mano de obra.
    """
    breakdown, meta = compute_repair_estimate(
        damaged_zone=damaged_zone,
        severity=severity,
        deductible=deductible,
        policy_type=policy_type,
    )

    payload = {
        "materiales": breakdown.materials,
        "mano_de_obra": breakdown.labor,
        "coste_bruto": breakdown.gross_total,
        "franquicia": breakdown.deductible,
        "total_a_pagar": breakdown.net_total,
        "zona_afectada": meta["zone_name"],
        "gravedad": meta["severity"],
        "detalle": meta["description"],
        "horas_estimadas": meta["estimated_hours"],
        "materials": breakdown.materials,
        "labor": breakdown.labor,
        "gross_total": breakdown.gross_total,
        "deductible": breakdown.deductible,
        "net_total": breakdown.net_total,
        "damaged_zone": meta["zone_name"],
        "severity": meta["severity"],
        "description": meta["description"],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
