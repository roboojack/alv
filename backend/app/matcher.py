from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from .config import Settings
from .schemas import CheckStatus, FieldCheck, VerificationPayload


_NORMALIZE_PATTERN = re.compile(r"[^A-Z0-9.% ]+")


def _normalize(text: str) -> str:
    upper = text.upper()
    collapsed = _NORMALIZE_PATTERN.sub(" ", upper)
    return " ".join(collapsed.split())


def _find_substring(haystack: str, needle: str) -> bool:
    return needle in haystack


def _parse_float(value: str) -> Optional[float]:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
    if not match:
        return None
    return float(match.group(1))


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
        r"[0-9]+\s*(?:ML|MILLILITERS)",
        r"[0-9]+\s*(?:L|LITERS)",
        r"[0-9]+\s*(?:FL\.?\s*OZ|OUNCES)",
    ]
    matches: List[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            matches.append(match.group(0))
    return matches


@dataclass
class MatcherContext:
    normalized_text: str
    raw_text: str
    token_set: set[str]


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


def check_brand(payload: VerificationPayload, ctx: MatcherContext) -> FieldCheck:
    target = _normalize(payload.brand_name)
    if target and (
        _find_substring(ctx.normalized_text, target)
        or _tokens_present(target, ctx.token_set)
    ):
        return FieldCheck(
            field="brand_name",
            status=CheckStatus.match,
            message="Brand name located on label",
            evidence=payload.brand_name,
            confidence=0.95,
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
    if target and _find_substring(ctx.normalized_text, target):
        return FieldCheck(
            field="product_class",
            status=CheckStatus.match,
            message="Product class/type string was detected",
            evidence=payload.product_class,
            confidence=0.9,
        )
    if target:
        tokens = target.split()
        hits = sum(1 for token in tokens if _token_similarity(token, ctx.token_set, 0.72))
        if hits / len(tokens) >= 0.75:
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
    if _find_substring(ctx.normalized_text, normalized_target):
        return FieldCheck(
            field="net_contents",
            status=CheckStatus.match,
            message="Net contents text detected",
            evidence=payload.net_contents,
            confidence=0.85,
        )
    detected = _extract_volume_strings(ctx.normalized_text)
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
        normalized_text=normalized_text, raw_text=raw_text, token_set=set(normalized_text.split())
    )
    results: List[FieldCheck] = []
    results.append(check_brand(payload, ctx))
    results.append(check_product_class(payload, ctx))
    results.append(check_alcohol_content(payload, ctx, settings))
    net = check_net_contents(payload, ctx)
    if net:
        results.append(net)
    gov = check_gov_warning(payload, ctx, settings)
    if gov:
        results.append(gov)
    return results
