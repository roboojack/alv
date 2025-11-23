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


def test_brand_fuzzy_match_handles_ocr_noise():
    payload = VerificationPayload(
        brand_name="di Amore",
        product_class="Sambuca",
        alcohol_content="42%",
            net_contents=None,
        require_gov_warning=False,
    )
    raw_lines = [
        "di Amore",
        "SAMBUCA",
        "Escape the ordinary with the magical romantic powers",
            "PRODUCT OF ITALY",
    ]
    results = matcher.run_all_checks(payload, raw_lines, get_settings())
    brand = next(check for check in results if check.field == "brand_name")
    assert brand.status.value == "MATCH"


def test_net_contents_matches_when_spacing_is_missing():
    payload = VerificationPayload(
        brand_name="Sample",
        product_class="Sample",
        alcohol_content="40%",
        net_contents="750 mL",
    )
    raw_lines = ["PRODUCT OF ITALY 750ML"]
    results = matcher.run_all_checks(payload, raw_lines, get_settings())
    net = next(check for check in results if check.field == "net_contents")
    assert net.status.value == "MATCH"


def test_net_contents_matches_equivalent_units():
    payload = VerificationPayload(
        brand_name="Sample",
        product_class="Sample",
        alcohol_content="40%",
        net_contents="25.4 fl oz",
    )
    raw_lines = ["BATCH 7 25.4FL.OZ"]
    results = matcher.run_all_checks(payload, raw_lines, get_settings())
    net = next(check for check in results if check.field == "net_contents")
    assert net.status.value == "MATCH"
