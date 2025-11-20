from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="session")
def labels_dir() -> Path:
    return Path(__file__).parent / "data" / "labels"


@pytest.fixture(scope="session")
def client() -> TestClient:
    app = create_app()
    return TestClient(app)
