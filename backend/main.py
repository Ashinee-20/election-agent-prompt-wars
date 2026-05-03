from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import Settings, get_settings
from backend.models import ChatRequest, ChatResponse, UserProfile, UserProfileResponse
from backend.services.adk_agent import ElectionAdkAgent
from backend.services.firestore_service import FirestoreService
from backend.services.maps_service import mock_polling_centers
from backend.services.timeline_service import eligibility_guidance, generate_timeline

settings = get_settings()
app = FastAPI(
    title="AI Election Assistant",
    description="Personalized election guidance powered by Gemini, Firestore, Firebase Auth, and Cloud Run.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

firestore_service = FirestoreService(settings)
agent = ElectionAdkAgent(settings)

app.mount("/static", StaticFiles(directory="frontend"), name="static")


def get_firestore() -> FirestoreService:
    return firestore_service


def verify_optional_firebase_token(
    authorization: str | None = Header(default=None),
    app_settings: Settings = Depends(get_settings),
) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    try:
        import firebase_admin
        from firebase_admin import auth, credentials

        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.ApplicationDefault(), {"projectId": app_settings.firebase_project_id})
        decoded = auth.verify_id_token(token)
        return decoded.get("uid")
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Firebase token verification failed: {exc}") from exc


@app.get("/")
def index() -> FileResponse:
    return FileResponse("frontend/index.html")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "firestore": firestore_service.enabled,
        "adk_available": agent.adk_available,
        "ai_framework": "Google ADK",
        "gemini_model": settings.gemini_model,
    }


@app.post("/user", response_model=UserProfileResponse)
def save_user(
    profile: UserProfile,
    uid: str | None = Depends(verify_optional_firebase_token),
    store: FirestoreService = Depends(get_firestore),
) -> UserProfileResponse:
    if uid:
        profile.user_id = uid
    saved = store.save_profile(profile)
    return UserProfileResponse(saved=saved, profile=profile, guidance=eligibility_guidance(profile))


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, store: FirestoreService = Depends(get_firestore)) -> ChatResponse:
    profile = request.profile or store.get_profile(request.user_id)
    store.append_chat(request.user_id, "user", request.message)
    history = store.get_chat_history(request.user_id)
    response, source = agent.run(request.message, profile, history)
    store.append_chat(request.user_id, "assistant", response)
    updated_history = store.get_chat_history(request.user_id)
    return ChatResponse(response=response, user_id=request.user_id, history=updated_history, data_source=source)


@app.get("/timeline")
def timeline(user_id: str = Query(default="demo-user"), store: FirestoreService = Depends(get_firestore)):
    profile = store.get_profile(user_id)
    return generate_timeline(user_id, profile)


@app.get("/polling-centers")
def polling_centers(user_id: str = Query(default="demo-user"), store: FirestoreService = Depends(get_firestore)):
    profile = store.get_profile(user_id)
    return {"user_id": user_id, "centers": mock_polling_centers(profile), "mode": "mock"}
