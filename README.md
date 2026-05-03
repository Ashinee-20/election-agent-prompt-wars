# AI-Powered Election Assistant

An interactive, full-stack Election Assistant that helps people understand voter eligibility, registration, required documents, timelines, polling-day steps, recent election updates, and result flow. The app uses FastAPI, an accessible frontend, Gemini on Google Cloud, Firestore, Firebase Auth-ready token validation, Google ADK-style multi-agent orchestration, Google Search grounding, Google Maps Platform-ready polling lookup, and Cloud Run deployment.

## Architecture

```text
Browser UI
  |  HTML/CSS/JS, accessible forms, quick action buttons
  v
FastAPI on Cloud Run
  |-- POST /user stores voter profile
  |-- POST /chat routes message to a specialist agent
  |-- GET /timeline builds election journey steps
  |-- GET /polling-centers returns Maps-ready polling lookup
  |
  |-- ElectionOrchestratorAgent classifies user intent
  |-- Specialist agents: eligibility, timeline, documents, polling, realtime, general
  |-- Gemini service using Google AI Studio API key or Vertex AI
  |-- Google Search grounding for recent/current election questions
  |-- Firestore service for profiles and chat history
  |-- Optional Firebase Auth bearer token verification
```

## Features

- Smart conversational assistant for questions like "How do I vote?", "Am I eligible?", and "What documents do I need?"
- Specialist agents for eligibility, timelines, documents, polling/maps, recent election updates, and general process questions.
- Google Search grounding for latest/recent election news, schedules, and results.
- Personalization by age, location, first-time voter status, and language.
- Firestore persistence for user profiles and chat history, with local in-memory fallback for demos.
- Decision logic for under-18 users, first-time voters, and returning voters.
- Dynamic timeline for registration, verification, voting day, and results.
- Google Maps Platform-ready polling lookup. When `GOOGLE_MAPS_API_KEY` is set, the backend calls Places Text Search; without a key it returns a clearly labeled demo fallback.
- Accessible UI with large readable text, semantic labels, keyboard-friendly controls, and clear steps.
- Secure configuration through environment variables only.

## Project Structure

```text
backend/
  main.py                    FastAPI app and API routes
  config.py                  Environment settings
  models.py                  Pydantic validation models
  services/
    adk_agent.py             Intent router and specialist election agents
    gemini_service.py        Gemini, Google Search, and Google Maps tool integration
    firestore_service.py     Firestore profile and chat storage
    timeline_service.py      Eligibility and timeline logic
    maps_service.py          Google Maps Platform / Places lookup service
  tests/
    test_api.py              API contract tests
    test_logic.py            Timeline and chat tests
    test_maps_service.py     Maps lookup tests
    test_models.py           Validation tests
    test_services.py         Agent and service tests
frontend/
  index.html                 Accessible single-page UI
  styles.css                 Responsive styling
  app.js                     API calls and UI interactions
Dockerfile                   Cloud Run container
requirements.txt             Python dependencies
.env.example                 Local configuration template
```

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload --port 8080
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn backend.main:app --reload --port 8080
```

Open `http://localhost:8080`.

## Environment

Set `GEMINI_API_KEY` for Google AI Studio, or set `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION` for Vertex AI.

Set `GOOGLE_MAPS_API_KEY` to enable live Google Places Text Search in `/polling-centers`. In production, store it in Secret Manager and mount it into Cloud Run with `--set-secrets`.

For local Firestore access, authenticate with Application Default Credentials:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

## API Design

### `POST /user`

```json
{
  "user_id": "demo-user",
  "age": 18,
  "location": "New Delhi",
  "first_time_voter": true,
  "language": "English"
}
```

### `POST /chat`

```json
{
  "user_id": "demo-user",
  "message": "What elections were completed recently?"
}
```

The response includes `agent`, `intent`, and `data_source`, for example `realtime_election_agent`, `realtime`, and `google-adk+gemini+google-search`.

### `GET /timeline?user_id=demo-user`

Returns personalized election steps.

### `GET /polling-centers?user_id=demo-user`

Returns live Google Places polling lookup when `GOOGLE_MAPS_API_KEY` is configured, otherwise a clearly labeled demo fallback.

## Tests

```bash
pytest -q
```

The repository includes focused unit and API tests for validation, timeline decision logic, Firestore fallback behavior, Gemini fallback behavior, ADK detection, specialist-agent routing, Maps lookup behavior, and deployed API contracts. A GitHub Actions workflow runs the same suite on push and pull request.

## Cloud Run Deployment

Enable required Google services:

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com aiplatform.googleapis.com artifactregistry.googleapis.com places.googleapis.com geocoding-backend.googleapis.com maps-backend.googleapis.com
```

Deploy from source:

```bash
gcloud run deploy election-assistant \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=true,FIREBASE_PROJECT_ID=YOUR_PROJECT_ID,GEMINI_MODEL=gemini-2.5-flash \
  --set-secrets GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY:latest
```

For Google AI Studio instead of Vertex AI, set `GEMINI_API_KEY` as a Cloud Run secret and keep `GOOGLE_GENAI_USE_VERTEXAI=false`.

## Google Services Used

- Gemini API: natural-language election guidance.
- Google ADK: specialist-agent orchestration pattern with an intent router.
- Google Search grounding: realtime election updates through Gemini tools.
- Firebase Firestore: user profile and chat history storage.
- Firebase Auth: optional identity verification through bearer tokens.
- Cloud Run: containerized FastAPI deployment.
- Cloud Build and Artifact Registry: source build and container storage for Cloud Run.
- Secret Manager: secure Maps API key storage for Cloud Run.
- Google Maps Platform: Places-ready polling center lookup through `GOOGLE_MAPS_API_KEY`.

## Security Notes

- API keys and project IDs are read from environment variables.
- Request bodies are validated with Pydantic.
- Firebase Auth token verification is optional but supported.
- The assistant is non-partisan and directs users to official election authorities for final legal rules.
