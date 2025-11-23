# Alcohol Label Verifier

**Live Demo:** [https://alv-2025.web.app/](https://alv-2025.web.app/)

AI-assisted toolkit that mirrors a simplified TTB review workflow. An Angular 18 SPA collects form submissions and label images, then a FastAPI service runs EasyOCR against the artwork and applies domain rules (brand, class/type, ABV, net contents, government warning). Results are streamed back with audible pass/fail cues so reviewers can keep cycling quickly.

## Stack
- **Backend** (`backend/`): FastAPI + EasyOCR + PyTorch, pytest suite with real bourbon label fixtures from Wikimedia Commons.
- **Frontend** (`label-verifier-ui/`): Angular 18 standalone app with reactive forms, drag-and-drop uploader, animated scoreboards, and pass/fail audio cues.
- **Fixtures**: `backend/tests/data/labels` contains three CC0/PD bourbon labels used both in tests and in the sample prefill buttons.

## Deployment Architecture

```mermaid
graph TD
    User[User Browser] -->|HTTPS| Firebase[Firebase Hosting]
    Firebase -->|Static Assets| Angular[Angular App]
    Firebase -->|/api/* Rewrites| CloudRun[Cloud Run (Backend)]
    CloudRun -->|OCR Processing| GPU[GPU/CPU Resources]
    CloudRun -->|Image Pull| GCR[Container Registry]
    GitHub[GitHub Repo] -->|Push| CloudBuild[Cloud Build]
    CloudBuild -->|Build & Push| GCR
    CloudBuild -->|Deploy| CloudRun
    CloudBuild -->|Deploy| Firebase
```

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (optional)

### Backend (FastAPI)

**Option 1: Python Virtual Environment (Mac/Linux/Windows)**

```bash
cd backend
python -m venv .venv

# Mac/Linux
source .venv/bin/activate

# Windows
# .venv\Scripts\activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.

**Option 2: Docker**

```bash
# Build the image
docker build -t alv-backend backend/

# Run the container
docker run -p 8000:8000 alv-backend
```

### Frontend (Angular)

```bash
cd label-verifier-ui
npm install
npm start
```
The application will run at `http://localhost:4200`. The dev server proxies API calls to `http://localhost:8000/api`.

## Running Tests

The backend includes a comprehensive test suite covering rule logic and end-to-end OCR flows.

```bash
cd backend
# Activate your virtual environment first
pytest
```
*Note: The first run downloads EasyOCR weights (~80 MB).*

## Deployment

The project is deployed on Google Cloud Platform using Cloud Run (Backend) and Firebase Hosting (Frontend).

### 1. Backend Deployment (Cloud Run)

We use Cloud Build to build the Docker image (supporting GPU) and deploy it to Cloud Run.

```bash
# Set your project
gcloud config set project alv-2025

# Submit build (uses backend/cloudbuild-gpu.yaml)
gcloud builds submit backend --config backend/cloudbuild-gpu.yaml

# Deploy to Cloud Run
gcloud run deploy alv-backend-gpu \
  --image gcr.io/alv-2025/alv-backend:gpu \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

### 2. Frontend Deployment (Firebase)

The frontend is hosted on Firebase, which also handles routing API requests to the Cloud Run backend.

```bash
cd label-verifier-ui

# Install and Build
npm install
npm run build

# Deploy to Firebase
firebase deploy
```

## Project Layout
```
backend/
  app/
    config.py           # runtime settings + matcher thresholds
    matcher.py          # brand/class/abv/net-content/government warning rules
    ocr.py              # OCR wrapper + preprocessing (EasyOCR default, Paddle-ready)
    services/           # VerifierService orchestrating OCR + rules
    main.py             # FastAPI wiring, multipart endpoint, CORS
  tests/
    data/labels/*.png   # Wikimedia Commons fixtures
    test_matcher.py     # unit tests for fuzzy matching logic
    test_api_verification.py  # end-to-end OCR checks with real images
label-verifier-ui/
  src/app/
    app.component.*     # reactive UI, drag-drop, scoreboard, sounds
    models.ts           # shared interfaces for API payloads
    verification.service.ts  # HTTP client wrapper
```

## Notes & Extensions
- Government warning detection defaults to required; disable per submission for legacy samples.
- `window.__ALV_API__` can be defined before app bootstrap to point the UI at a remote backend without rebuilding.
- Future ideas: highlight OCR bounding boxes, multi-product workflows, or queue integrations.

