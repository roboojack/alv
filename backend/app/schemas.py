from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ProductType(str, Enum):
    spirits = "spirits"
    wine = "wine"
    beer = "beer"


class VerificationPayload(BaseModel):
    brand_name: str = Field(..., description="Brand listed on the submission form")
    product_class: str = Field(..., description="Class/type text supplied by the producer")
    alcohol_content: str = Field(..., description="ABV value such as '45%' or '13.5%'")
    net_contents: Optional[str] = Field(
        default=None, description="Net contents string, e.g. '750 mL' or '12 FL OZ'"
    )
    product_type: ProductType = ProductType.spirits
    require_gov_warning: bool = True


class CheckStatus(str, Enum):
    match = "MATCH"
    mismatch = "MISMATCH"
    missing = "MISSING"
    error = "ERROR"


class FieldCheck(BaseModel):
    field: str
    status: CheckStatus
    message: str
    evidence: Optional[str] = None
    confidence: Optional[float] = None


class VerificationResponse(BaseModel):
    status: str
    duration_ms: float
    checks: List[FieldCheck]
    ocr_tokens: List[str]
    raw_ocr_text: str
