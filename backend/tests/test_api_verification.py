import json

import pytest


@pytest.mark.parametrize(
    "filename,payload,expected_status",
    [
        (
            "trey_herring.png",
            {
                "brand_name": "Trey Herring's",
                "product_class": "Carolina Bourbon Whiskey",
                "alcohol_content": "45%",
                "net_contents": None,
                "require_gov_warning": False,
            },
            "PASS",
        ),
        (
            "ringside_bourbon.jpg",
            {
                "brand_name": "RINGSIDE",
                "product_class": "Kentucky Straight Bourbon Whiskey",
                "alcohol_content": "90 PROOF",
                "net_contents": None,
                "require_gov_warning": False,
            },
            "PASS",
        ),
        (
            "di_amore_sambuca.jpg",
            {
                "brand_name": "di Amore",
                "product_class": "Sambuca",
                "alcohol_content": "42%",
                "net_contents": None,
                "require_gov_warning": False,
            },
            "PASS",
        ),
        (
            "PXL_20251123_002746096.MP.jpg",
            {
                "brand_name": "Mogen David",
                "product_class": "Blackberry Wine",
                "alcohol_content": "10%",
                "net_contents": None,
                "require_gov_warning": False,
            },
            "PASS",
        ),
        (
            "PXL_20251123_002749276.MP.jpg",
            {
                "brand_name": "Mogen David",
                "product_class": "Blackberry Wine",
                "alcohol_content": "10%",
                "net_contents": None,
                "require_gov_warning": False,
            },
            "PASS",
        ),
    ],
)
def test_verify_success_cases(client, labels_dir, filename, payload, expected_status):
    data = {"form_payload": json.dumps(payload)}
    file_path = labels_dir / filename
    with file_path.open("rb") as fh:
        content_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
        files = {"image": (file_path.name, fh, content_type)}
        response = client.post("/api/verify", data=data, files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == expected_status
    assert all(check["status"] == "MATCH" for check in body["checks"])


def test_verify_flags_missing_abv(client, labels_dir):
    payload = {
        "brand_name": "La Sylphide",
        "product_class": "Bourbon Whiskey",
        "alcohol_content": "45%",
        "net_contents": None,
        "require_gov_warning": False,
    }
    data = {"form_payload": json.dumps(payload)}
    file_path = labels_dir / "la_sylphide.jpg"
    with file_path.open("rb") as fh:
        files = {"image": (file_path.name, fh, "image/jpeg")}
        response = client.post("/api/verify", data=data, files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAIL"
    abv = next(check for check in body["checks"] if check["field"] == "alcohol_content")
    assert abv["status"] in {"MISSING", "MISMATCH"}


@pytest.mark.parametrize(
    "filename,payload",
    [
        (
            "black_ridge.jpg",
            {
                "brand_name": "Black Ridge",
                "product_class": "Kentucky Straight Bourbon Whiskey",
                "alcohol_content": "90 PROOF",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "bushmills.jpg",
            {
                "brand_name": "Bushmills",
                "product_class": "Irish Whiskey",
                "alcohol_content": "40%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "old_crow.jpg",
            {
                "brand_name": "Old Crow",
                "product_class": "Kentucky Straight Bourbon Whiskey",
                "alcohol_content": "80 PROOF",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "our_house_rye.jpg",
            {
                "brand_name": "Our House",
                "product_class": "Rye Whiskey",
                "alcohol_content": "45%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
    ],
)
def test_verify_failure_cases(client, labels_dir, filename, payload):
    data = {"form_payload": json.dumps(payload)}
    file_path = labels_dir / filename
    with file_path.open("rb") as fh:
        content_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
        files = {"image": (file_path.name, fh, content_type)}
        response = client.post("/api/verify", data=data, files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAIL"
    # alcohol_content should be missing or mismatch for these labels currently
    abv = next(check for check in body["checks"] if check["field"] == "alcohol_content")
    assert abv["status"] in {"MISSING", "MISMATCH"}


@pytest.mark.parametrize(
    "filename,payload",
    [
        (
            "PXL_20251123_002758795.MP.jpg",
            {
                "brand_name": "425 Wine Co",
                "product_class": "Kosher Wine",
                "alcohol_content": "12%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_002949433.MP.jpg",
            {
                "brand_name": "Grand Blue",
                "product_class": "Brandy",
                "alcohol_content": "80 PROOF",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003001585.MP.jpg",
            {
                "brand_name": "EX Brandy",
                "product_class": "American Brandy",
                "alcohol_content": "40%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003115920.MP.jpg",
            {
                "brand_name": "DeKuyper Anisette",
                "product_class": "Anisette Liqueur",
                "alcohol_content": "30%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003123218.MP.jpg",
            {
                "brand_name": "DeKuyper Coffee Liqueur",
                "product_class": "Coffee Liqueur",
                "alcohol_content": "35%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003226283.MP.jpg",
            {
                "brand_name": "La Hacienda",
                "product_class": "Tequila",
                "alcohol_content": "40%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003232036.MP.jpg",
            {
                "brand_name": "La Hacienda",
                "product_class": "Tequila",
                "alcohol_content": "40%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003240620.MP.jpg",
            {
                "brand_name": "D2",
                "product_class": "Spirit",
                "alcohol_content": "38%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003247288.MP.jpg",
            {
                "brand_name": "Cactus Jack",
                "product_class": "Tequila",
                "alcohol_content": "40%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003338174.MP.jpg",
            {
                "brand_name": "Canadian Mist",
                "product_class": "Canadian Whisky",
                "alcohol_content": "40%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003355093.MP.jpg",
            {
                "brand_name": "Canadian Mist",
                "product_class": "Canadian Whisky",
                "alcohol_content": "40%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003454651.MP.jpg",
            {
                "brand_name": "Gem Clear",
                "product_class": "Neutral Spirit",
                "alcohol_content": "95%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003504471.MP.jpg",
            {
                "brand_name": "TC",
                "product_class": "Spirit",
                "alcohol_content": "22%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003610755.MP.jpg",
            {
                "brand_name": "Bacardi Gold",
                "product_class": "Rum",
                "alcohol_content": "40%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
        (
            "PXL_20251123_003620523.MP.jpg",
            {
                "brand_name": "Bacardi Gold",
                "product_class": "Rum",
                "alcohol_content": "40%",
                "net_contents": None,
                "require_gov_warning": False,
            },
        ),
    ],
)
def test_verify_pxl_failure_cases(client, labels_dir, filename, payload):
    data = {"form_payload": json.dumps(payload)}
    file_path = labels_dir / filename
    with file_path.open("rb") as fh:
        content_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
        files = {"image": (file_path.name, fh, content_type)}
        response = client.post("/api/verify", data=data, files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAIL"
    assert any(check["status"] != "MATCH" for check in body["checks"])
