# Copilot Instructions

These notes capture the conventions that make contributors productive quickly.

## Architecture Snapshot
- Backend lives in `backend/app` (FastAPI) and exposes `POST /api/verify`; frontend lives in `label-verifier-ui` (Angular 18 standalone) and consumes the same endpoint via `VerificationService`.
- Verification flow: Angular form → FastAPI endpoint → `VerifierService` → Google Gemini VLM (2.5 Flash) → response with per-field verdicts, OCR tokens, raw text.
- Sample bourbon labels from Wikimedia Commons sit in `backend/tests/data/labels` and double as manual QA fixtures (prefill buttons in the UI reference those payloads).

## Backend Guidelines
- Configuration (`app/config.py`) holds matcher thresholds and CORS origins; fetch with `get_settings()` instead of instantiating `Settings` manually so env overrides work.
- Service layer (`services/verifier_service.py`) is the core logic hub. It constructs the VLM prompt, calls Gemini, and parses the JSON response.
- If you add new dependencies (databases, S3, etc.), extend this service and inject via FastAPI dependency wiring.
- Tests must cover both rule logic and VLM integration. Use pytest fixtures (`tests/conftest.py`) plus the real label images to prove end-to-end behavior.
- Commands: `cd backend && ./run_tests.sh` (or `pytest -n auto`) for suites, `uvicorn app.main:app --reload` for local API.

## Frontend Guidelines
- Angular app is standalone (no NgModules). `AppComponent` imports `CommonModule` + `ReactiveFormsModule`; keep new UI in standalone components or feature directories when expanding.
- API calls go through `src/app/verification.service.ts`. It reads `window.__ALV_API__` (optional) and defaults to `http://localhost:8000/api`. Do not hardcode endpoints elsewhere; inject the service.
- State management is kept inside `AppComponent` with reactive forms. Use `FormBuilder` + signals/inject if new complex sections arise. Respect existing helpers (`handleDragOver`, `resetForm`, `useFixture`).
- Styling relies on CSS variables defined in `src/styles.scss` and glassmorphism cards inside `app.component.scss`. Stay within that system (cards, pills, status chips) and adjust `angular.json` style budgets if you add large stylesheets.
- Audio cues live under `src/assets/audio`. To add more, drop files there so Angular build tooling copies them automatically (configured in `angular.json`).
- Build/test commands: `cd label-verifier-ui && npm run build` for type-checking; unit specs live next to components (see `app.component.spec.ts` with HttpClientTestingModule).

## Developer Workflows
- Use the provided sample fixtures via the UI buttons or by posting multiparts with the JSON bodies in `tests/test_api_verification.py`.
- When tweaking OCR thresholds, update both `Settings.matcher_thresholds` and the tests—they assert on matches/mismatches for real images.
- Keep the README up to date with run instructions. Any new env var should be documented in `backend/.env.example` (create if needed) and referenced in the instructions file.
- **Security**: Ensure that no secrets or sensitive data (API keys, credentials) are ever committed to the repository. Use `.env` files and environment variables.
