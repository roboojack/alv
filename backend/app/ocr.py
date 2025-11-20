from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from typing import List

import easyocr
import numpy as np
from PIL import Image, ImageFilter, ImageOps

from .config import Settings, get_settings


@dataclass
class OCRResult:
    tokens: List[str]
    raw_lines: List[str]

    @property
    def combined_text(self) -> str:
        return " ".join(self.raw_lines)


def _preprocess(image_bytes: bytes) -> Image.Image:
    image = Image.open(BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)  # normalize orientation
    grayscale = ImageOps.grayscale(image)
    enhanced = grayscale.filter(ImageFilter.MedianFilter(size=3))
    return enhanced


@lru_cache
def _get_reader(languages: tuple[str, ...], gpu: bool) -> easyocr.Reader:
    return easyocr.Reader(list(languages), gpu=gpu)


def run_ocr(image_bytes: bytes, settings: Settings | None = None) -> OCRResult:
    config = settings or get_settings()
    processed = _preprocess(image_bytes)
    np_image = np.array(processed)
    reader = _get_reader(tuple(config.ocr_languages), config.use_gpu)
    results = reader.readtext(np_image)

    tokens: List[str] = []
    raw_lines: List[str] = []
    for bbox, text, confidence in results:
        normalized = text.strip()
        if not normalized:
            continue
        raw_lines.append(normalized)
        if (
            confidence >= config.matcher_thresholds.token_confidence_floor
            and len(normalized) >= config.matcher_thresholds.min_token_length
        ):
            tokens.append(normalized)

    return OCRResult(tokens=tokens, raw_lines=raw_lines)
