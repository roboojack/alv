from functools import lru_cache
from typing import List

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class MatcherThresholds(BaseModel):
    abv_tolerance_percent: float = 0.5  # +/- 0.5% ABV allowance
    token_confidence_floor: float = 0.35
    min_token_length: int = 2
    brand_token_similarity: float = 0.72
    brand_token_match_fraction: float = 0.5


class Settings(BaseSettings):
    """Runtime configuration for the verifier service."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ALV_", extra="ignore")

    project_name: str = "Alcohol Label Verifier API"
    api_prefix: str = "/api"
    cors_origins: List[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ]
    ocr_languages: List[str] = ["en"]
    use_gpu: bool = False
    gemini_api_key: str = ""
    matcher_thresholds: MatcherThresholds = MatcherThresholds()
    gov_warning_phrase: str = "GOVERNMENT WARNING"
    gov_warning_snippet: str = (
        "ACCORDING TO THE SURGEON GENERAL"
    )  # partial match to keep OCR lenient


@lru_cache
def get_settings() -> Settings:
    return Settings()
