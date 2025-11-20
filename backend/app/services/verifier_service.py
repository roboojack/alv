from __future__ import annotations

import time
from typing import Tuple

from fastapi import UploadFile

from .. import matcher, ocr
from ..config import Settings, get_settings
from ..schemas import CheckStatus, FieldCheck, VerificationPayload, VerificationResponse


class VerifierService:
    """Coordinates OCR + rule evaluation for a single request."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def verify(self, payload: VerificationPayload, image: UploadFile) -> VerificationResponse:
        image_bytes = await image.read()
        start = time.perf_counter()
        ocr_result = ocr.run_ocr(image_bytes, self.settings)
        checks: Tuple[FieldCheck, ...] = tuple(
            matcher.run_all_checks(payload, ocr_result.raw_lines, self.settings)
        )
        duration = (time.perf_counter() - start) * 1000
        status = "PASS" if all(check.status == CheckStatus.match for check in checks) else "FAIL"
        return VerificationResponse(
            status=status,
            duration_ms=round(duration, 2),
            checks=list(checks),
            ocr_tokens=ocr_result.tokens,
            raw_ocr_text=ocr_result.combined_text,
        )


def get_verifier_service() -> VerifierService:
    return VerifierService()
