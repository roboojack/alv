# Alcohol Label Verifier

**Live Demo:** [https://alv-2025.web.app/](https://alv-2025.web.app/)

AI-assisted toolkit that mirrors a simplified TTB review workflow. An Angular 18 SPA collects form submissions and label images, then a FastAPI service uses Google Gemini (VLM) to analyze the artwork and verify domain rules (brand, class/type, ABV, net contents, government warning). Results are streamed back with audible pass/fail cues so reviewers can keep cycling quickly.

## Stack
- **Backend** (`backend/`): FastAPI + Google Gemini 2.5 Flash, pytest suite with real bourbon label fixtures.
- **Frontend** (`label-verifier-ui/`): Angular 18 standalone app with reactive forms, drag-and-drop uploader, animated scoreboards, and pass/fail audio cues.
- **Fixtures**: `backend/tests/data/labels` contains real label images used both in tests and in the sample prefill buttons.

## Configuration
You must provide a Google Gemini API Key.
1. Create a `.env` file in `backend/` (see `backend/.env.example`).
2. Add `ALV_GEMINI_API_KEY=your_key_here`.

## Deployment Architecture

```mermaid
graph TD
    User[User Browser] -->|HTTPS| Firebase[Firebase Hosting]
    Firebase -->|Static Assets| Angular[Angular App]
    Firebase -->|/api/* Rewrites| CloudRun["Cloud Run (Backend)"]
    CloudRun -->|VLM Analysis| Gemini["Google Gemini API"]
    CloudRun -->|Image Pull| GCR[Container Registry]
    
    subgraph Backend_Workflow [Backend Deployment]
    CloudBuild[Cloud Build] -->|Build, Push & Deploy| CloudRun
    end
    
    subgraph Frontend_Workflow [Frontend Deployment]
    CLI[Firebase CLI] -->|Deploy| Firebase
    end
```

## Matching Logic

The verification engine uses Google Gemini 2.5 Flash to perform OCR and semantic verification in a single pass.

```mermaid
graph TD
    Start["Input: Form Payload + Label Image"] --> Prompt["Construct VLM Prompt"]
    Prompt --> Gemini["Gemini 2.5 Flash"]
    Gemini -->|JSON Response| Result["Verification Report"]
```

## Running Locally

### Quick Start
We provide helper scripts to spin up both the backend (FastAPI) and frontend (Angular) in one go.

**Mac / Linux**
```bash
chmod +x start.sh
./start.sh
```

**Windows**
```cmd
start.bat
```

The app will open at `http://localhost:4200` and the API at `http://localhost:8000`.

### Manual Setup

If you prefer to run services individually or use Docker:

#### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (optional)

#### Backend (FastAPI)

**Option 1: Python Virtual Environment**

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

The backend includes a comprehensive test suite covering rule logic and end-to-end VLM flows.

```bash
cd backend
# Activate your virtual environment first
pytest
```

## Deployment

The project is deployed on Google Cloud Platform using Cloud Run (Backend) and Firebase Hosting (Frontend).

### 1. Backend Deployment (Cloud Run)

We use Cloud Build to build the Docker image and deploy it to Cloud Run.

```bash
# Set your project
gcloud config set project alv-2025

# Submit build (uses backend/cloudbuild.yaml)
# This command builds the image, pushes it to GCR, and deploys to Cloud Run.
gcloud builds submit backend --config backend/cloudbuild.yaml
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
    services/           # VerifierService orchestrating VLM calls
    main.py             # FastAPI wiring, multipart endpoint, CORS
  tests/
    data/labels/*.png   # Wikimedia Commons fixtures
    test_api_verification.py  # end-to-end VLM checks with real images
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

