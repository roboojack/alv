# Alcohol Label Verifier – Architecture Plan

## High-Level Overview
- **Goal**: Intake structured form data + label image, run VLM analysis, and report match/mismatch per compliance rule, exposing a FastAPI backend and an Angular SPA frontend.
- **Stack**:
  - Backend: Python 3.11, FastAPI, Google Gemini 2.5 Flash, Pydantic, Uvicorn, pytest + httpx for tests.
  - Frontend: Angular 18 (standalone components), Tailwind-like utility styling via CSS variables, ngx-toastr? (opt) but we will stick to custom components.
  - Assets: Real bourbon label images sourced from Wikimedia Commons, stored under `backend/tests/data/labels` for deterministic tests.

## Backend Modules (`backend/app`)
1. `config.py`: Centralized settings (API keys, thresholds, version info).
2. `schemas.py`: Pydantic models for requests (form fields) and responses (per-field verdicts, summary, OCR debug dump).
3. `routes.py` / `main.py`: FastAPI app with `/api/health` and `/api/verify` (multipart form + file). Integrates CORS for Angular dev (`http://localhost:4200`).
4. `services/verifier_service.py`: Orchestrates Gemini VLM pipeline and aggregates scoreboard metrics for UI.

## Backend Data Flow
1. Angular posts `multipart/form-data` containing JSON string for form payload + binary image.
2. FastAPI constructs a prompt for Gemini 2.5 Flash, including the image and the form data.
3. Gemini analyzes the image and compares it against the form data, returning a structured JSON response.
4. Response includes:
   ```json
   {
     "overallStatus": "PASS" | "FAIL" | "ERROR",
     "checks": [{"field": "brandName", "status": "MATCH", "details": "Brand name found twice", "evidence": "TREY HERRING"}],
     "ocrSample": [...top tokens...]
   }
   ```

## Test Strategy
- **Integration**: pytest with FastAPI TestClient hitting `/api/verify` using real label image fixtures (downloaded into repo). Ensures VLM integration.
- **Golden Assets**: `Trey_Herring`, `La_Sylphide`, `Ringside` labels. Provide expected form inputs for match/mismatch scenarios.

## Frontend (`frontend/label-verifier-ui`)
1. Angular standalone app with feature modules:
   - `app/core`: API service (`verification.service.ts`), environment config.
   - `app/components/form-panel`: Reactive form for data input & file upload w/ preview.
   - `app/components/result-panel`: Displays list of checks, highlights mismatches, plays success/fail audio.
   - `app/components/history-timeline`: Optional recent submissions list (local state) for UX.
2. Styling: CSS variables for dark navy + amber palette, glassmorphism cards, animated status chips.
3. Assets: `assets/audio/success-chime.wav`, `assets/audio/failure-buzzer.wav` generated programmatically, plus placeholder hero illustration.
4. Behavior: After submission, show progress loader (Angular Material progress bar or custom), then scoreboard with confetti for pass and shaking card + buzzer for fail.

## Dev Experience
- Backend: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload`.
- Frontend: `cd frontend/label-verifier-ui && npm install && npm start` proxied to backend.
- Tests: `pytest` for backend; future work could add Cypress/Playwright for UI.

## Deployment Thoughts
- Containerize backend (FastAPI + Uvicorn) and frontend (Angular build served via nginx) when ready. Provide `.env.example` for config.

This plan satisfies the take-home requirements while leaving room for stretch goals like highlighting OCR bounding boxes or multi-product workflows.
