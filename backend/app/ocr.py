from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from typing import List, cast

import easyocr
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from .config import Settings, get_settings


@dataclass
class OCRResult:
    tokens: List[str]
    raw_lines: List[str]

    @property
    def combined_text(self) -> str:
        return " ".join(self.raw_lines)


MAX_IMAGE_SIDE = 3072


def _preprocess(image_bytes: bytes) -> Image.Image:
    image: Image.Image = Image.open(BytesIO(image_bytes))
    image = cast(Image.Image, ImageOps.exif_transpose(image))  # normalize orientation
    if image.mode != "RGB":
        image = image.convert("RGB")
    longest_edge = max(image.size)
    if longest_edge > MAX_IMAGE_SIDE:
        scale = MAX_IMAGE_SIDE / longest_edge
        new_size = (
            max(1, int(image.width * scale)),
            max(1, int(image.height * scale)),
        )
        # Downscale aggressively to keep OCR under Firebase's 60s proxy limit
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    boosted = ImageOps.autocontrast(image, cutoff=2)
    contrast = ImageEnhance.Contrast(boosted).enhance(1.2)
    sharpened = ImageEnhance.Sharpness(contrast).enhance(1.15)
    denoised = sharpened.filter(ImageFilter.MedianFilter(size=3))
    return denoised


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
            float(confidence) >= config.matcher_thresholds.token_confidence_floor
            and len(normalized) >= config.matcher_thresholds.min_token_length
        ):
            tokens.append(normalized)

    return OCRResult(tokens=tokens, raw_lines=raw_lines)
