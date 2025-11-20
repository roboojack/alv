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
                "brand_name": "Quality Distillers",
                "product_class": "Kentucky Straight Bourbon Whiskey",
                "alcohol_content": "45%",
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
        files = {"image": (file_path.name, fh, "image/png")}
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
