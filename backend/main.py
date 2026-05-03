import base64

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

try:
    import firebase_admin
    from firebase_admin import auth, credentials
except ImportError:
    firebase_admin = None
    auth = None
    credentials = None

from backend.config import Settings, get_settings
from backend.models import ChatRequest, ChatResponse, PollingCentersResponse, TimelineResponse, UserProfile, UserProfileResponse
from backend.services.adk_agent import ElectionAdkAgent
from backend.services.firestore_service import FirestoreService
from backend.services.maps_service import lookup_polling_centers
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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

firestore_service = FirestoreService(settings)
agent = ElectionAdkAgent(settings)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

FAVICON_BYTES = base64.b64decode(
    "AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A"
    "////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A"
    "////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A"
    "////AP///wD///8A////AP///wD///8A"
)


def get_firestore() -> FirestoreService:
    return firestore_service


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; connect-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:"
    return response


def verify_optional_firebase_token(
    authorization: str | None = Header(default=None),
    app_settings: Settings = Depends(get_settings),
) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    if not firebase_admin or not auth or not credentials:
        raise HTTPException(status_code=401, detail="Firebase token verification failed")
    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.ApplicationDefault(), {"projectId": app_settings.firebase_project_id})
        decoded = auth.verify_id_token(token)
        return decoded.get("uid")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Firebase token verification failed") from exc


@app.get("/")
def index() -> FileResponse:
    return FileResponse("frontend/index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(content=FAVICON_BYTES, media_type="image/x-icon")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "firestore": firestore_service.enabled,
        "adk_available": agent.adk_available,
        "adk_app_built": agent.adk_app is not None,
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
    result = agent.run(request.message, profile, history)
    store.append_chat(request.user_id, "assistant", result.response)
    updated_history = store.get_chat_history(request.user_id)
    return ChatResponse(
        response=result.response,
        user_id=request.user_id,
        history=updated_history,
        data_source=result.source,
        agent=result.agent,
        intent=result.intent,
    )


@app.get("/timeline", response_model=TimelineResponse)
def timeline(user_id: str = Query(default="demo-user"), store: FirestoreService = Depends(get_firestore)) -> TimelineResponse:
    profile = store.get_profile(user_id)
    return generate_timeline(user_id, profile)


@app.get("/polling-centers", response_model=PollingCentersResponse)
async def polling_centers(user_id: str = Query(default="demo-user"), store: FirestoreService = Depends(get_firestore)) -> PollingCentersResponse:
    profile = store.get_profile(user_id)
    result = await lookup_polling_centers(profile, settings)
    return PollingCentersResponse(user_id=user_id, **result)
