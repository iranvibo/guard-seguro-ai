"""PII Masking and Unmasking engine for Responsible AI compliance.

Detects sensitive personally identifiable information (PII) including Spanish DNIs/NIEs,
phone numbers, vehicle license plates, email addresses, IBANs, postal addresses,
and person names, replacing them with reversible pseudo-tokens.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from src.core.models import AnonymizedClaim, ClaimInput
from src.privacy.patterns import (
    COMMON_SPANISH_FIRST_NAMES,
    COMMON_SPANISH_SURNAMES,
    PATTERN_CONTEXTUAL_NAME,
    PATTERN_DIRECCION,
    PATTERN_DNI_NIE,
    PATTERN_EMAIL,
    PATTERN_IBAN,
    PATTERN_MATRICULA,
    PATTERN_TELEFONO,
)


@dataclass
class _EntitySpan:
    """Internal helper to represent a matched PII span in raw text."""

    start: int
    end: int
    entity_type: str
    text: str


class PIIMasker:
    """Core PII masking and unmasking processor for insurance claims."""

    def __init__(
        self,
        enable_dni: bool = True,
        enable_phone: bool = True,
        enable_plate: bool = True,
        enable_email: bool = True,
        enable_iban: bool = True,
        enable_address: bool = True,
        enable_name: bool = True,
    ) -> None:
        self.enable_dni = enable_dni
        self.enable_phone = enable_phone
        self.enable_plate = enable_plate
        self.enable_email = enable_email
        self.enable_iban = enable_iban
        self.enable_address = enable_address
        self.enable_name = enable_name

    def _find_spans(self, text: str) -> List[_EntitySpan]:
        """Detect all PII entity spans matching configured patterns."""
        spans: List[_EntitySpan] = []

        # 1. Emails
        if self.enable_email:
            for match in PATTERN_EMAIL.finditer(text):
                spans.append(
                    _EntitySpan(
                        start=match.start(),
                        end=match.end(),
                        entity_type="EMAIL",
                        text=match.group(),
                    )
                )

        # 2. IBANs
        if self.enable_iban:
            for match in PATTERN_IBAN.finditer(text):
                spans.append(
                    _EntitySpan(
                        start=match.start(),
                        end=match.end(),
                        entity_type="IBAN",
                        text=match.group(),
                    )
                )

        # 3. DNI / NIE
        if self.enable_dni:
            for match in PATTERN_DNI_NIE.finditer(text):
                spans.append(
                    _EntitySpan(
                        start=match.start(),
                        end=match.end(),
                        entity_type="DNI",
                        text=match.group(),
                    )
                )

        # 4. License Plates (Matrículas)
        if self.enable_plate:
            for match in PATTERN_MATRICULA.finditer(text):
                spans.append(
                    _EntitySpan(
                        start=match.start(),
                        end=match.end(),
                        entity_type="MATRICULA",
                        text=match.group(),
                    )
                )

        # 5. Phone numbers (Teléfonos)
        if self.enable_phone:
            for match in PATTERN_TELEFONO.finditer(text):
                raw = match.group().strip()
                spans.append(
                    _EntitySpan(
                        start=match.start(),
                        end=match.end(),
                        entity_type="TELEFONO",
                        text=raw,
                    )
                )

        # 6. Addresses (Direcciones)
        if self.enable_address:
            for match in PATTERN_DIRECCION.finditer(text):
                addr_text = match.group().strip()
                spans.append(
                    _EntitySpan(
                        start=match.start(),
                        end=match.start() + len(addr_text),
                        entity_type="DIRECCION",
                        text=addr_text,
                    )
                )

        # 7. Person Names (Nombres propios)
        if self.enable_name:
            # A) Contextual name matches ("El cliente Juan Pérez...")
            for match in PATTERN_CONTEXTUAL_NAME.finditer(text):
                name_match = match.group(1).strip()
                name_start = match.start(1)
                name_end = name_start + len(name_match)
                spans.append(
                    _EntitySpan(
                        start=name_start,
                        end=name_end,
                        entity_type="PERSONA",
                        text=name_match,
                    )
                )

            # B) Gazetteer name matching (e.g. FirstName + Surnames sequence)
            self._find_gazetteer_name_spans(text, spans)

        return spans

    def _find_gazetteer_name_spans(self, text: str, spans: List[_EntitySpan]) -> None:
        """Scan text words for contiguous sequences matching known Spanish names and surnames."""
        for match in re.finditer(
            r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)"
            r"(?:\s+(?:de\s+la\s+|de\s+|del\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3}\b",
            text,
            re.UNICODE,
        ):
            full_match_text = match.group(0)
            words = [
                w.lower()
                for w in re.findall(r"\b[A-ZÁÉÍÓÚÑa-záéíóúñ]+\b", full_match_text)
            ]
            main_words = [w for w in words if w not in {"de", "la", "del"}]
            if not main_words or len(main_words) < 2:
                continue
            first_word = main_words[0]
            if first_word in COMMON_SPANISH_FIRST_NAMES:
                all_valid = all(
                    w in COMMON_SPANISH_SURNAMES or w in COMMON_SPANISH_FIRST_NAMES
                    for w in main_words[1:]
                )
                if all_valid:
                    spans.append(
                        _EntitySpan(
                            start=match.start(),
                            end=match.end(),
                            entity_type="PERSONA",
                            text=full_match_text,
                        )
                    )

    def _resolve_overlapping_spans(self, spans: List[_EntitySpan]) -> List[_EntitySpan]:
        """Resolve overlapping spans prioritizing longer matches and earlier start positions."""
        if not spans:
            return []

        # Sort primarily by start asc, length desc
        sorted_spans = sorted(
            spans,
            key=lambda s: (s.start, -(s.end - s.start)),
        )

        resolved: List[_EntitySpan] = []
        last_end = -1

        for span in sorted_spans:
            if span.start >= last_end:
                resolved.append(span)
                last_end = span.end
            elif span.end > last_end and span.start == resolved[-1].start:
                resolved[-1] = span
                last_end = span.end

        return resolved

    def mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Mask PII entities in given text.

        Returns:
            Tuple of (masked_text, pii_mapping) where pii_mapping is {placeholder: original_value}.
        """
        if not text:
            return "", {}

        raw_spans = self._find_spans(text)
        spans = self._resolve_overlapping_spans(raw_spans)

        if not spans:
            return text, {}

        # Track placeholder assignments consistently
        value_to_placeholder: Dict[str, str] = {}
        counters: Dict[str, int] = {}
        pii_mapping: Dict[str, str] = {}

        pieces: List[str] = []
        last_idx = 0

        for span in spans:
            pieces.append(text[last_idx : span.start])

            val = span.text
            norm_val = val.strip()

            if norm_val in value_to_placeholder:
                placeholder = value_to_placeholder[norm_val]
            else:
                curr_count = counters.get(span.entity_type, 0) + 1
                counters[span.entity_type] = curr_count
                placeholder = f"[{span.entity_type}_{curr_count}]"
                value_to_placeholder[norm_val] = placeholder
                pii_mapping[placeholder] = norm_val

            pieces.append(placeholder)
            last_idx = span.end

        pieces.append(text[last_idx:])
        masked_text = "".join(pieces)

        return masked_text, pii_mapping

    def unmask(self, text: str, pii_mapping: Dict[str, str]) -> str:
        """Restore original PII data into masked text using mapping dictionary.

        Args:
            text: Text containing pseudo-tokens (e.g., [PERSONA_1]).
            pii_mapping: Mapping {placeholder: original_value}.

        Returns:
            Unmasked text with original entities restored.
        """
        if not text or not pii_mapping:
            return text

        result = text
        sorted_tokens = sorted(pii_mapping.keys(), key=len, reverse=True)

        for token in sorted_tokens:
            original_val = pii_mapping[token]
            result = result.replace(token, original_val)

        return result

    def anonymize_claim(self, claim_input: ClaimInput) -> AnonymizedClaim:
        """Convenience method to transform a ClaimInput into a typed AnonymizedClaim."""
        masked_text, pii_mapping = self.mask(claim_input.raw_text)
        return AnonymizedClaim(
            claim_id=claim_input.claim_id,
            original_text=claim_input.raw_text,
            anonymized_text=masked_text,
            pii_mapping=pii_mapping,
            detected_entities_count=len(pii_mapping),
        )


# ---------------------------------------------------------------------------
# Module-level Convenience Functions (matching DoD requirements)
# ---------------------------------------------------------------------------

_DEFAULT_MASKER = PIIMasker()


def mask_pii(text: str) -> Tuple[str, Dict[str, str]]:
    """Identifies and replaces sensitive personal data (DNI, phones, plates, names, emails, addresses).

    Args:
        text: Original raw claim or communication text.

    Returns:
        Tuple of (masked_text, pii_mapping).
    """
    return _DEFAULT_MASKER.mask(text)


def unmask_pii(text: str, pii_mapping: Dict[str, str]) -> str:
    """Restores original PII data in the response text using the mapping dictionary.

    Args:
        text: Anonymized response or assessment text.
        pii_mapping: Mapping of pseudo-tokens to original strings.

    Returns:
        Restored text for human insurance handlers.
    """
    return _DEFAULT_MASKER.unmask(text, pii_mapping)


def anonymize_claim(claim_input: ClaimInput) -> AnonymizedClaim:
    """Processes a ClaimInput schema into an AnonymizedClaim schema."""
    return _DEFAULT_MASKER.anonymize_claim(claim_input)
