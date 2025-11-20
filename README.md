# Alcohol Label Verifier

AI-assisted toolkit that mirrors a simplified TTB review workflow. An Angular 18 SPA collects form submissions and label images, then a FastAPI service runs EasyOCR against the artwork and applies domain rules (brand, class/type, ABV, net contents, government warning). Results are streamed back with audible pass/fail cues so reviewers can keep cycling quickly.

## Stack
- **Backend** (`backend/`): FastAPI + EasyOCR + PyTorch, pytest suite with real bourbon label fixtures from Wikimedia Commons.
- **Frontend** (`label-verifier-ui/`): Angular 18 standalone app with reactive forms, drag-and-drop uploader, animated scoreboards, and pass/fail audio cues.
- **Fixtures**: `backend/tests/data/labels` contains three CC0/PD bourbon labels used both in tests and in the sample prefill buttons.

## Running the backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
The API exposes `GET /api/health` and `POST /api/verify`, which expects `multipart/form-data` with a `form_payload` JSON string and an `image` file.

### Tests
```bash
cd backend
pytest
```
The suite covers rule logic and full OCR+comparison flows using the downloaded fixtures. The first run downloads EasyOCR weights (~80 MB).

## Running the Angular SPA
```bash
cd label-verifier-ui
npm install
npm start
```
The dev server proxies the API calls directly to `http://localhost:8000/api` (CORS is open to localhost:4200). Production builds are available via `npm run build`.

### UI tips
- Drag & drop or click the neon dropzone to attach JPEG/PNG labels.
- Use the preset buttons (Trey Herring, Ringside, La Sylphide) to autofill the form to match bundled fixtures.
- Pass/fail sounds are stored under `src/assets/audio` and play after each verification. OCR tokens and raw text are visible in the "OCR Highlights" panel for debugging.

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

## Deploying on Google Cloud Free Tier
The backend runs on Cloud Run (fully managed) and the Angular bundle is served from Firebase Hosting, which proxies `/api/*` to Cloud Run so the browser never needs to know the service URL.

### 1. Build and deploy the Cloud Run service
```bash
PROJECT_ID="your-gcp-project"
SERVICE_NAME="alv-backend"
REGION="us-central1"

gcloud auth login
gcloud config set project "$PROJECT_ID"
gcloud builds submit backend --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME"
gcloud run deploy "$SERVICE_NAME" \
  --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --min-instances 0 \
  --max-instances 1
```
The first request downloads ~80 MB of EasyOCR weights, so give the container a minute on cold start. Note the HTTPS URL Cloud Run returns (e.g. `https://alv-backend-xxxxx-uc.a.run.app`).

### 2. Configure Firebase Hosting for the SPA
Update `.firebaserc` with your Firebase project ID, and edit `firebase.json` so `serviceId` matches the Cloud Run service name/region. Then build and deploy the Angular app:
```bash
cd label-verifier-ui
npm install
npm run build -- --configuration production
cd ..

firebase login
firebase use YOUR_FIREBASE_PROJECT_ID
firebase deploy --only hosting
```
Firebase rewrites `/api/**` calls to Cloud Run, so the UI just calls `/api` and the `src/assets/runtime-config.js` script keeps local development pointed at `http://localhost:8000/api`.

## CI/CD
Pushing to the `develop` branch runs `.github/workflows/deploy.yml`, which:

1. Submits `backend/` to Cloud Build, then deploys the resulting image to Cloud Run (`alv-backend`).
2. Builds the Angular bundle with `npm run build -- --configuration production` and deploys it to Firebase Hosting (which already rewrites `/api/*` to the Cloud Run service).

Create the following GitHub repository secrets before pushing:

| Secret | Description |
| --- | --- |
| `GCP_PROJECT_ID` | Google Cloud project that hosts Cloud Run + Cloud Build. |
| `GCP_SA_KEY` | JSON key for a service account with `Cloud Run Admin`, `Cloud Build Editor`, `Service Account User`, and `Storage Admin` roles. |
| `FIREBASE_PROJECT_ID` | Firebase Hosting project ID (usually matches the GCP project). |
| `FIREBASE_SERVICE_ACCOUNT` | JSON key for a service account with `Firebase Hosting Admin` + `Cloud Run Invoker` rights. |

Optional: Add `SLACK_WEBHOOK_URL` (or similar) if you extend the workflow with notifications.
