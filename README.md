# AI-Powered Election Assistant

An interactive, full-stack Election Assistant that helps people understand voter eligibility, registration, required documents, timelines, polling-day steps, and result flow. The app uses FastAPI, a clean accessible frontend, Gemini, Firestore, Firebase Auth-ready token validation, Google ADK-friendly orchestration, and Cloud Run deployment.

## Architecture

```text
Browser UI
  |  HTML/CSS/JS, accessible forms, quick action buttons
  v
FastAPI on Cloud Run
  |-- POST /user stores voter profile
  |-- POST /chat answers personalized questions
  |-- GET /timeline builds election journey steps
  |-- GET /polling-centers returns mocked polling lookup
  |
  |-- Google ADK wrapper
  |-- Gemini service using Google AI Studio API key or Vertex AI
  |-- Firestore service for profiles and chat history
  |-- Optional Firebase Auth bearer token verification
```

## Features

- Smart conversational assistant for questions like “How do I vote?”, “Am I eligible?”, and “What documents do I need?”
- Personalization by age, location, first-time voter status, and language.
- Firestore persistence for user profiles and chat history, with local in-memory fallback for demos.
- Decision logic for under-18 users, first-time voters, and returning voters.
- Dynamic timeline for registration, verification, voting day, and results.
- Mock polling center lookup that can be replaced with Google Maps API.
- Accessible UI with large readable text, semantic labels, keyboard-friendly controls, and clear steps.
- Secure configuration through environment variables only.

## Project Structure

```text
backend/
  main.py                    FastAPI app and API routes
  config.py                  Environment settings
  models.py                  Pydantic validation models
  services/
    adk_agent.py             Google ADK-friendly orchestration wrapper
    gemini_service.py        Gemini integration
    firestore_service.py     Firestore profile and chat storage
    timeline_service.py      Eligibility and timeline logic
    maps_service.py          Mock polling center lookup
  tests/
    test_logic.py            Focused API and logic tests
frontend/
  index.html                 Accessible single-page UI
  styles.css                 Responsive styling
  app.js                     API calls and UI interactions
Dockerfile                   Cloud Run container
requirements.txt             Python dependencies
.env.example                 Local configuration template
```

## Local Setup

1. Create a virtual environment and install dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Create local environment variables.

```bash
cp .env.example .env
```

Set `GEMINI_API_KEY` for Google AI Studio, or set `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION` for Vertex AI.

3. Run the app.

```bash
uvicorn backend.main:app --reload --port 8080
```

Open `http://localhost:8080`.

## Firestore And Firebase Auth

For local Firestore access, authenticate with Application Default Credentials:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Then set:

```bash
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
FIREBASE_PROJECT_ID=YOUR_PROJECT_ID
```

The `/user` endpoint accepts an optional Firebase Auth bearer token. When present, the backend verifies it and uses the Firebase UID as the user ID. Without credentials, the app runs in local demo mode so judges can still test the workflow.

## API Design

### `POST /user`

Saves the profile.

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

Returns a personalized assistant response and stores chat history.

```json
{
  "user_id": "demo-user",
  "message": "What documents do I need?"
}
```

### `GET /timeline?user_id=demo-user`

Returns personalized election steps.

## Tests

```bash
pytest -q
```

The repository includes focused unit and API tests for validation, timeline decision logic, Firestore fallback behavior, Gemini fallback behavior, ADK detection, and deployed API contracts. A GitHub Actions workflow runs the same suite on push and pull request.

## Cloud Run Deployment

1. Enable required Google services.

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com aiplatform.googleapis.com
```

2. Deploy from source.

```bash
gcloud run deploy election-assistant \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=true,FIREBASE_PROJECT_ID=YOUR_PROJECT_ID,GEMINI_MODEL=gemini-2.5-flash
```

For Google AI Studio instead of Vertex AI, set `GEMINI_API_KEY` as a Cloud Run secret and keep `GOOGLE_GENAI_USE_VERTEXAI=false`.

3. Cloud Run prints a public service URL after deployment. Use that URL as the deployed link for the challenge submission.

## Google Services Used

- Gemini API: natural-language election guidance.
- Google ADK: assistant orchestration wrapper, with fallback for local execution.
- Firebase Firestore: user profile and chat history storage.
- Firebase Auth: optional identity verification through bearer tokens.
- Cloud Run: containerized FastAPI deployment.
- Google Maps API-ready design: polling center endpoint currently mocked to keep the repository lightweight.

## Security Notes

- API keys and project IDs are read from environment variables.
- Request bodies are validated with Pydantic.
- Firebase Auth token verification is optional but supported.
- The assistant is non-partisan and directs users to official election authorities for final legal rules.
