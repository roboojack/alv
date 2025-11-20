from app import matcher
from app.config import get_settings
from app.schemas import VerificationPayload


def test_brand_tokens_match_when_discontinuous():
    payload = VerificationPayload(
        brand_name="Trey Herring's",
        product_class="Carolina Bourbon Whiskey",
        alcohol_content="45%",
        net_contents=None,
    )
    raw_lines = ["TREY", "HERRING 'S", "CAROLINA BOURBON WHISKEY", "45%"]
    results = matcher.run_all_checks(payload, raw_lines, get_settings())
    brand_check = next(check for check in results if check.field == "brand_name")
    assert brand_check.status.value == "MATCH"


def test_abv_detection_handles_proof_values():
    payload = VerificationPayload(
        brand_name="Sample",
        product_class="Sample",
        alcohol_content="45%",
        net_contents=None,
    )
    raw_lines = ["RINGSIDE", "90 PROOF"]
    results = matcher.run_all_checks(payload, raw_lines, get_settings())
    abv = next(check for check in results if check.field == "alcohol_content")
    assert abv.status.value == "MATCH"
