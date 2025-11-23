"""Utility to inspect PXL_2025*.jpg label images and emit heuristic guesses.

Run:
    cd backend
    ../.venv/bin/python scripts/inspect_pxl_labels.py

Outputs JSON lines with file name, size, token sample, brand guess and product guess.
This avoids adding unverified test expectations prematurely.
"""

from __future__ import annotations

import json
from pathlib import Path

import sys

# Ensure backend package import works when executed via relative path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_ROOT))
from app.config import get_settings  # type: ignore  # noqa: E402
from app.ocr import run_ocr  # type: ignore  # noqa: E402


KEYWORD_TO_CLASS = [
    ("bourbon", "Bourbon Whiskey"),
    ("straight bourbon", "Kentucky Straight Bourbon Whiskey"),
    ("rye", "Rye Whiskey"),
    ("whiskey", "Whiskey"),
    ("gin", "Gin"),
    ("vodka", "Vodka"),
    ("rum", "Rum"),
    ("sambuca", "Sambuca"),
]


def guess_product_class(text: str) -> str:
    low = text.lower()
    for kw, cls in KEYWORD_TO_CLASS:
        if kw in low:
            return cls
    return ""


def main() -> None:
    settings = get_settings()
    # When running from within backend, tests/data/labels lives at ../backend/tests/data/labels relative to this script
    labels_dir = (BACKEND_ROOT / "tests" / "data" / "labels").resolve()
    pxl_files = sorted(
        [p for p in labels_dir.iterdir() if p.name.startswith("PXL_2025") and p.suffix.lower() == ".jpg"]
    )
    for path in pxl_files:
        with path.open("rb") as fh:
            img_bytes = fh.read()
        try:
            ocr = run_ocr(img_bytes, settings)
            # Some OCRResult variants may not expose raw_text; fallback to tokens
            raw_text = getattr(ocr, "raw_text", " ".join(getattr(ocr, "tokens", [])))
            tokens = raw_text.split()
            upper_tokens = [t for t in tokens if t.isupper() and len(t) > 2]
            brand_guess = upper_tokens[0] if upper_tokens else (tokens[0] if tokens else "")
            product_guess = guess_product_class(raw_text)
            out = {
                "file": path.name,
                "size_bytes": path.stat().st_size,
                "brand_guess": brand_guess,
                "product_guess": product_guess,
                "token_sample": tokens[:15],
                "raw_excerpt": raw_text.replace("\n", " ")[:250],
            }
        except Exception as e:  # noqa: BLE001
            out = {"file": path.name, "size_bytes": path.stat().st_size, "error": str(e)}
        print(json.dumps(out))


if __name__ == "__main__":  # pragma: no cover
    main()
