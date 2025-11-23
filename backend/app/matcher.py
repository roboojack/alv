from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from .config import Settings
from .schemas import CheckStatus, FieldCheck, VerificationPayload


_NORMALIZE_PATTERN = re.compile(r"[^A-Z0-9.% ]+")
_VOLUME_PARSE_PATTERN = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)\s*(ML|MILLILITERS|L|LITERS|FL\.?\s*OZ|OUNCES)",
    re.IGNORECASE,
)

# Synonyms for product class matching (e.g. Spanish/French terms on labels)
_CLASS_SYNONYMS = {
    "RON": "RUM",
    "RHUM": "RUM",
    "VODKA": "VODKA",
    "WHISKEY": "WHISKY",
    "WHISKY": "WHISKEY",
    "GIN": "GIN",
    "TEQUILA": "TEQUILA",
    "MEZCAL": "MEZCAL",
    "BRANDY": "BRANDY",
    "COGNAC": "COGNAC",
    "BOURBON": "BOURBON",
    "SCOTCH": "SCOTCH",
    "LIQUEUR": "LIQUEUR",
    "CORDIAL": "CORDIAL",
    "ORO": "GOLD",
    "PLATA": "SILVER",
    "BLANCO": "SILVER",
    "ANEJO": "AGED",
    "REPOSADO": "RESTED",
}


def _compact(text: str) -> str:
    return text.replace(" ", "")


def _normalize(text: str) -> str:
    upper = text.upper()
    collapsed = _NORMALIZE_PATTERN.sub(" ", upper)
    return " ".join(collapsed.split())


def _aggressive_normalize_for_matching(text: str) -> str:
    """
    Aggressive normalization to handle 'G 0 L D' vs 'GOLD' and '0' vs 'O'.
    Removes spaces and maps 0->O.
    """
    norm = _normalize(text)
    # Map 0 to O to handle OCR confusion in text fields (risky for numbers, use carefully)
    norm = norm.replace("0", "O")
    return _compact(norm)


def _find_substring(haystack: str, needle: str) -> bool:
    return needle in haystack


def _parse_float(value: str) -> Optional[float]:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
    if not match:
        return None
    amount = float(match.group(1))
    if "PROOF" in value.upper():
        return round(amount / 2.0, 1)
    return amount


def _extract_abv_candidates(text: str) -> List[float]:
    percents: List[float] = []
    for match in re.finditer(r"([0-9]{1,3}(?:\.[0-9]+)?)\s*%", text):
        percents.append(float(match.group(1)))
    for match in re.finditer(r"([0-9]{2,3})\s*PROOF", text):
        proof_value = float(match.group(1))
        percents.append(round(proof_value / 2.0, 1))
    return percents


def _extract_volume_strings(text: str) -> List[str]:
    patterns = [
        r"[0-9]+(?:\.[0-9]+)?\s*(?:ML|MILLILITERS)",
        r"[0-9]+(?:\.[0-9]+)?\s*(?:L|LITERS)",
        r"[0-9]+(?:\.[0-9]+)?\s*(?:FL\.?\s*OZ|OUNCES)",
    ]
    matches: List[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            matches.append(match.group(0))
    return matches


def _canonicalize_volume_value(value: str | None) -> Optional[float]:
    if not value:
        return None
    prepared = value.upper()
    prepared = prepared.replace("FL.OZ", "FLOZ")
    prepared = prepared.replace("FL. OZ", "FLOZ")
    prepared = re.sub(r"\s+", " ", prepared)
    match = _VOLUME_PARSE_PATTERN.search(prepared)
    if not match:
        return None
    amount = float(match.group(1))
    unit_key = re.sub(r"[^A-Z]", "", match.group(2).upper())
    multiplier = {
        "ML": 1.0,
        "MILLILITERS": 1.0,
        "L": 1000.0,
        "LITERS": 1000.0,
        "FLOZ": 29.5735,
        "OUNCES": 29.5735,
    }.get(unit_key)
    if multiplier is None:
        return None
    return round(amount * multiplier, 2)


@dataclass
class MatcherContext:
    normalized_text: str
    raw_text: str
    token_set: set[str]
    # Derived context for advanced matching
    aggressive_text: str


def _tokens_present(target: str, token_set: set[str]) -> bool:
    tokens = target.split()
    return all(token in token_set for token in tokens)


def _token_similarity(word: str, existing: set[str], threshold: float = 0.8) -> bool:
    if word in existing:
        return True
    for candidate in existing:
        if difflib.SequenceMatcher(None, word, candidate).ratio() >= threshold:
            return True
    return False


def check_brand(
    payload: VerificationPayload, ctx: MatcherContext, settings: Settings
) -> FieldCheck:
    target = _normalize(payload.brand_name)
    if not target:
        return FieldCheck(
            field="brand_name",
            status=CheckStatus.mismatch,
            message="Brand name is empty",
            evidence=payload.brand_name,
            confidence=0.0,
        )

    # 1. Exact substring match
    if _find_substring(ctx.normalized_text, target) or _tokens_present(target, ctx.token_set):
        return FieldCheck(
            field="brand_name",
            status=CheckStatus.match,
            message="Brand name located on label",
            evidence=payload.brand_name,
            confidence=0.95,
        )

    # 2. Aggressive match (ignoring spaces and 0/O confusion)
    aggressive_target = _aggressive_normalize_for_matching(target)
    if aggressive_target and aggressive_target in ctx.aggressive_text:
        return FieldCheck(
            field="brand_name",
            status=CheckStatus.match,
            message="Brand name detected (fuzzy space/char match)",
            evidence=payload.brand_name,
            confidence=0.85,
        )

    # 3. Token-based fuzzy match
    tokens = target.split()
    if tokens:
        similarity = settings.matcher_thresholds.brand_token_similarity
        required_fraction = settings.matcher_thresholds.brand_token_match_fraction
        hits = sum(
            1
            for token in tokens
            if _token_similarity(token, ctx.token_set, similarity)
        )
        if hits and hits / len(tokens) >= required_fraction:
            return FieldCheck(
                field="brand_name",
                status=CheckStatus.match,
                message="Brand name inferred from fuzzy token matches",
                evidence=payload.brand_name,
                confidence=0.72,
            )

    return FieldCheck(
        field="brand_name",
        status=CheckStatus.mismatch,
        message="Brand name text was not detected in the OCR output",
        evidence=payload.brand_name,
        confidence=0.2,
    )


def check_product_class(payload: VerificationPayload, ctx: MatcherContext) -> FieldCheck:
    target = _normalize(payload.product_class)
    if not target:
        return FieldCheck(
            field="product_class",
            status=CheckStatus.mismatch,
            message="Product class is empty",
            evidence=payload.product_class,
            confidence=0.0,
        )

    # 1. Exact match
    if _find_substring(ctx.normalized_text, target):
        return FieldCheck(
            field="product_class",
            status=CheckStatus.match,
            message="Product class/type string was detected",
            evidence=payload.product_class,
            confidence=0.9,
        )

    # 2. Synonym match (e.g. RON -> RUM)
    # Check if any synonym of the target class appears in the text
    # Invert the map to find synonyms for the target
    synonyms = [k for k, v in _CLASS_SYNONYMS.items() if v == target]
    for synonym in synonyms:
        if _find_substring(ctx.normalized_text, synonym) or _tokens_present(synonym, ctx.token_set):
             return FieldCheck(
                field="product_class",
                status=CheckStatus.match,
                message=f"Product class detected via synonym '{synonym}'",
                evidence=payload.product_class,
                confidence=0.85,
            )
    
    target_tokens = target.split()

    # 3. Fuzzy token match
    hits = sum(1 for token in target_tokens if _token_similarity(token, ctx.token_set, 0.72))
    if hits / len(target_tokens) >= 0.75:
        return FieldCheck(
            field="product_class",
            status=CheckStatus.match,
            message="Majority of class/type keywords surfaced despite OCR noise",
            evidence=payload.product_class,
            confidence=0.75,
        )

    return FieldCheck(
        field="product_class",
        status=CheckStatus.mismatch,
        message="Product class/type phrase missing from OCR text",
        evidence=payload.product_class,
        confidence=0.25,
    )


def check_alcohol_content(
    payload: VerificationPayload, ctx: MatcherContext, settings: Settings
) -> FieldCheck:
    expected = _parse_float(payload.alcohol_content)
    if expected is None:
        return FieldCheck(
            field="alcohol_content",
            status=CheckStatus.error,
            message="Unable to parse alcohol content from form submission",
            evidence=payload.alcohol_content,
        )
    matches = _extract_abv_candidates(ctx.normalized_text)
    if not matches:
        return FieldCheck(
            field="alcohol_content",
            status=CheckStatus.missing,
            message="No ABV or proof markings were detected on the label",
            evidence=payload.alcohol_content,
            confidence=0.1,
        )
    tolerance = settings.matcher_thresholds.abv_tolerance_percent
    for candidate in matches:
        if abs(candidate - expected) <= tolerance:
            return FieldCheck(
                field="alcohol_content",
                status=CheckStatus.match,
                message=f"Detected {candidate}% which is within ±{tolerance}% of expected",
                evidence=f"{candidate}%",
                confidence=0.9,
            )
    return FieldCheck(
        field="alcohol_content",
        status=CheckStatus.mismatch,
        message=f"Detected ABV readings {matches} do not align with expected {expected}%",
        evidence=payload.alcohol_content,
        confidence=0.3,
    )


def check_net_contents(payload: VerificationPayload, ctx: MatcherContext) -> Optional[FieldCheck]:
    if not payload.net_contents:
        return None
    normalized_target = _normalize(payload.net_contents)
    
    # 1. Exact match
    if _find_substring(ctx.normalized_text, normalized_target):
        return FieldCheck(
            field="net_contents",
            status=CheckStatus.match,
            message="Net contents text detected",
            evidence=payload.net_contents,
            confidence=0.85,
        )

    # 2. Compact match (ignore spaces)
    no_space_target = _compact(normalized_target)
    if no_space_target and no_space_target in _compact(ctx.normalized_text):
        return FieldCheck(
            field="net_contents",
            status=CheckStatus.match,
            message="Net contents detected after ignoring spacing noise",
            evidence=payload.net_contents,
            confidence=0.82,
        )

    # 3. "Missing Decimal" match (e.g. 1.75 L -> 175 L)
    # Remove dots from target and check if it exists in compact text
    no_dot_target = no_space_target.replace(".", "")
    if no_dot_target and no_dot_target in _compact(ctx.normalized_text):
         return FieldCheck(
            field="net_contents",
            status=CheckStatus.match,
            message="Net contents detected (ignoring decimal point)",
            evidence=payload.net_contents,
            confidence=0.75,
        )

    # 4. Fuzzy Volume Match (e.g. 1.76 L vs 1.75 L, or 175 L vs 1.75 L)
    canonical_expected = _canonicalize_volume_value(payload.net_contents)
    if canonical_expected is not None:
        # Extract candidates from compact text: digits followed by unit
        compact_text = _compact(ctx.normalized_text)
        # Regex for digits followed by unit (L, ML, FLOZ, etc)
        # Units: L, ML, FLOZ, OZ. In compact text: L, ML, FLOZ, OZ.
        # Note: OUNCES -> OUNCES.
        candidates = re.finditer(r"(\d+)(ML|L|FLOZ|OZ|OUNCES|LITERS|MILLILITERS)", compact_text)
        for match in candidates:
            digits = match.group(1)
            unit = match.group(2)
            # Try scaling the digits: 176 -> 176, 17.6, 1.76, 0.176
            val = float(digits)
            scales = [1.0, 0.1, 0.01, 0.001]
            
            # Get unit multiplier
            unit_key = re.sub(r"[^A-Z]", "", unit.upper())
            multiplier = {
                "ML": 1.0, "MILLILITERS": 1.0,
                "L": 1000.0, "LITERS": 1000.0,
                "FLOZ": 29.5735, "OZ": 29.5735, "OUNCES": 29.5735
            }.get(unit_key, 1.0)

            for scale in scales:
                scaled_val = val * scale
                canonical_candidate = scaled_val * multiplier
                # Allow 5% tolerance or 0.5 ML/OZ absolute?
                # Use relative tolerance for safety
                if abs(canonical_candidate - canonical_expected) / canonical_expected < 0.05:
                     return FieldCheck(
                        field="net_contents",
                        status=CheckStatus.match,
                        message=f"Net contents inferred from '{digits}{unit}' (interpreted as {scaled_val} {unit})",
                        evidence=payload.net_contents,
                        confidence=0.7,
                    )

    # 5. Volume parsing match (standard)
    detected = _extract_volume_strings(ctx.normalized_text)
    canonical_expected = _canonicalize_volume_value(payload.net_contents)
    if canonical_expected is not None:
        for candidate in detected:
            candidate_value = _canonicalize_volume_value(candidate)
            if candidate_value is None:
                continue
            if abs(candidate_value - canonical_expected) <= 0.5:
                return FieldCheck(
                    field="net_contents",
                    status=CheckStatus.match,
                    message="Net contents detected via equivalent volume reading",
                    evidence=payload.net_contents,
                    confidence=0.83,
                )
    if detected:
        return FieldCheck(
            field="net_contents",
            status=CheckStatus.mismatch,
            message=f"Found {detected} which does not match expected {payload.net_contents}",
            evidence=payload.net_contents,
            confidence=0.4,
        )
    return FieldCheck(
        field="net_contents",
        status=CheckStatus.missing,
        message="No net contents text surfaced in OCR",
        evidence=payload.net_contents,
        confidence=0.2,
    )


def check_gov_warning(payload: VerificationPayload, ctx: MatcherContext, settings: Settings) -> Optional[FieldCheck]:
    if not payload.require_gov_warning:
        return None
    normalized = ctx.normalized_text
    phrase = _normalize(settings.gov_warning_phrase)
    snippet = _normalize(settings.gov_warning_snippet)
    phrase_found = _find_substring(normalized, phrase)
    snippet_found = _find_substring(normalized, snippet)
    if phrase_found and snippet_found:
        return FieldCheck(
            field="government_warning",
            status=CheckStatus.match,
            message="Government warning headline and snippet detected",
            evidence=settings.gov_warning_phrase,
            confidence=0.88,
        )
    if phrase_found or snippet_found:
        return FieldCheck(
            field="government_warning",
            status=CheckStatus.mismatch,
            message="Partial government warning detected; wording incomplete",
            evidence=settings.gov_warning_phrase,
            confidence=0.5,
        )
    return FieldCheck(
        field="government_warning",
        status=CheckStatus.missing,
        message="Government warning block absent",
        evidence=settings.gov_warning_phrase,
        confidence=0.2,
    )


def run_all_checks(
    payload: VerificationPayload, raw_lines: Iterable[str], settings: Settings
) -> List[FieldCheck]:
    raw_text = " ".join(raw_lines)
    normalized_text = _normalize(raw_text)
    ctx = MatcherContext(
        normalized_text=normalized_text,
        raw_text=raw_text,
        token_set=set(normalized_text.split()),
        aggressive_text=_aggressive_normalize_for_matching(raw_text)
    )
    results: List[FieldCheck] = []
    results.append(check_brand(payload, ctx, settings))
    results.append(check_product_class(payload, ctx))
    results.append(check_alcohol_content(payload, ctx, settings))
    net = check_net_contents(payload, ctx)
    if net:
        results.append(net)
    gov = check_gov_warning(payload, ctx, settings)
    if gov:
        results.append(gov)
    return results
