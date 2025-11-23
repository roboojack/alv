from __future__ import annotations

import json
import time
import os
import io
from typing import List, Optional

import google.generativeai as genai
from fastapi import UploadFile, HTTPException
from PIL import Image

from ..config import Settings, get_settings
from ..schemas import CheckStatus, FieldCheck, VerificationPayload, VerificationResponse


class VerifierService:
    """Coordinates verification using Google Gemini VLM."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        
        # Ensure API key is available
        api_key = self.settings.gemini_api_key or os.getenv("ALV_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("WARNING: GEMINI_API_KEY not set. Verification will fail.")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                'gemini-2.5-flash',
                generation_config=genai.GenerationConfig(temperature=0.0)
            )

    async def verify(self, payload: VerificationPayload, image: UploadFile) -> VerificationResponse:
        # Re-check API key at runtime to allow env var injection after startup
        if not getattr(self, 'model', None):
             api_key = self.settings.gemini_api_key or os.getenv("ALV_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
             if api_key:
                 genai.configure(api_key=api_key)
                 self.model = genai.GenerativeModel(
                     'gemini-2.5-flash',
                     generation_config=genai.GenerationConfig(temperature=0.0)
                 )
             else:
                 raise HTTPException(status_code=500, detail="Server misconfiguration: Missing Gemini API Key")

        image_bytes = await image.read()
        start = time.perf_counter()
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # Optimization: Resize large images to speed up inference
            # Max dimension 1024px is usually sufficient for OCR on labels
            if img.width > 1024 or img.height > 1024:
                img.thumbnail((1024, 1024))
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

        prompt = self._build_prompt(payload)
        
        try:
            response = self.model.generate_content([prompt, img])
            result_json = self._parse_response(response.text)
        except Exception as e:
            print(f"Gemini Error: {e}")
            # Fallback for parsing errors or API errors
            raise HTTPException(status_code=502, detail=f"Upstream verification service failed: {e}")

        duration = (time.perf_counter() - start) * 1000
        
        checks = [FieldCheck(**c) for c in result_json.get("checks", [])]
        
        # Determine overall status
        # If any check is MISMATCH or MISSING, then FAIL.
        status = "PASS"
        for check in checks:
            if check.status != CheckStatus.match:
                status = "FAIL"
                break
        
        return VerificationResponse(
            status=status,
            duration_ms=round(duration, 2),
            checks=checks,
            ocr_tokens=result_json.get("ocr_tokens", []),
            raw_ocr_text=result_json.get("raw_ocr_text", "")
        )

    def _build_prompt(self, payload: VerificationPayload) -> str:
        gov_warning_instruction = ""
        if payload.require_gov_warning:
            gov_warning_instruction = """
                {
                    "field": "government_warning",
                    "status": "MATCH" | "MISMATCH" | "MISSING",
                    "message": "Check for 'GOVERNMENT WARNING' text",
                    "evidence": "Text found..."
                },
            """

        return f"""
        You are an expert Alcohol and Tobacco Tax and Trade Bureau (TTB) label specialist.
        Your task is to verify if the provided alcohol label image matches the data submitted in the form.

        Form Data:
        - Brand Name: "{payload.brand_name}"
        - Product Class/Type: "{payload.product_class}"
        - Alcohol Content (ABV): "{payload.alcohol_content}"
        - Net Contents: "{payload.net_contents or 'Not Specified'}"
        - Require Government Warning: {"Yes" if payload.require_gov_warning else "No"}

        Instructions:
        1. Extract all text from the label (OCR).
        2. Compare the Form Data against the label text.
           - Brand Name: Look for the brand name. It might be stylized. Fuzzy match is okay (e.g. "Trey Herring's" matches "Trey Herring").
           - Product Class: Look for the class/type (e.g., "Bourbon Whiskey", "Vodka").
           - ABV: Look for the alcohol percentage. BE STRICT. "40%" does NOT match "45%". "80 PROOF" matches "40% ALC/VOL".
           - Net Contents: Look for volume (e.g., "750mL", "1 L"). If 'Not Specified' in form, return MATCH unless you clearly see a volume that contradicts standard sizes.
           - Government Warning: If required, check if the standard "GOVERNMENT WARNING" text is present.

        3. Output a JSON object with the following structure (do not include markdown formatting like ```json):
        {{
            "checks": [
                {{
                    "field": "brand_name",
                    "status": "MATCH" | "MISMATCH" | "MISSING",
                    "message": "Brief explanation",
                    "evidence": "The text found on the label that supports this"
                }},
                {{
                    "field": "product_class",
                    "status": "MATCH" | "MISMATCH" | "MISSING",
                    "message": "...",
                    "evidence": "..."
                }},
                {{
                    "field": "alcohol_content",
                    "status": "MATCH" | "MISMATCH" | "MISSING",
                    "message": "...",
                    "evidence": "..."
                }},
                {{
                    "field": "net_contents",
                    "status": "MATCH" | "MISMATCH" | "MISSING",
                    "message": "...",
                    "evidence": "..."
                }},
                {gov_warning_instruction}
            ],
            "raw_ocr_text": "The full text extracted from the label...",
            "ocr_tokens": ["list", "of", "all", "words", "found"]
        }}
        """

    def _parse_response(self, text: str) -> dict:
        try:
            # Find the first '{' and last '}'
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                json_str = text[start : end + 1]
                return json.loads(json_str)
            else:
                # Fallback to original cleanup if braces not found (unlikely)
                text = text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                return json.loads(text)
        except json.JSONDecodeError:
            # Last ditch effort: try to repair common JSON errors or just fail
            print(f"Failed to parse JSON: {text}")
            raise


def get_verifier_service() -> VerifierService:
    return VerifierService()
