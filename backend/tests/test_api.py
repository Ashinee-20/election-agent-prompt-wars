import asyncio

from backend.main import app
from backend.tests.utils import get_path, post_json


def test_health_endpoint_reports_runtime_flags():
    response = asyncio.run(get_path(app, "/health"))
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert "firestore" in payload
    assert "gemini_model" in payload
    assert payload["ai_framework"] == "Google ADK"
    assert "adk_app_built" in payload
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_user_endpoint_saves_profile_and_returns_guidance():
    response = asyncio.run(
        post_json(
            app,
            "/user",
            {
                "user_id": "api-user",
                "age": 17,
                "location": "Chennai",
                "first_time_voter": True,
                "language": "English",
            },
        )
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["profile"]["location"] == "Chennai"
    assert "not eligible" in payload["guidance"].lower()


def test_timeline_endpoint_uses_saved_profile():
    asyncio.run(
        post_json(
            app,
            "/user",
            {
                "user_id": "timeline-user",
                "age": 22,
                "location": "Pune",
                "first_time_voter": False,
                "language": "English",
            },
        )
    )
    response = asyncio.run(get_path(app, "/timeline?user_id=timeline-user"))
    payload = response.json()
    assert response.status_code == 200
    assert payload["generated_for"]["first_time_voter"] is False
    assert "existing voter record" in payload["steps"][0]["description"]


def test_polling_centers_are_location_aware_mock_results():
    asyncio.run(
        post_json(
            app,
            "/user",
            {
                "user_id": "center-user",
                "age": 35,
                "location": "Hyderabad",
                "first_time_voter": False,
                "language": "English",
            },
        )
    )
    response = asyncio.run(get_path(app, "/polling-centers?user_id=center-user"))
    payload = response.json()
    assert response.status_code == 200
    assert payload["mode"] == "mock-google-maps-api-key-missing"
    assert "Hyderabad" in payload["centers"][0]["address"]
    assert "centers" in payload


def test_invalid_chat_input_is_rejected():
    response = asyncio.run(post_json(app, "/chat", {"user_id": "bad", "message": ""}))
    assert response.status_code == 422


def test_chat_response_includes_agent_metadata():
    response = asyncio.run(
        post_json(
            app,
            "/chat",
            {
                "user_id": "agent-meta-user",
                "message": "What documents do I need?",
                "profile": {"user_id": "agent-meta-user", "age": 22, "location": "Delhi", "first_time_voter": True},
            },
        )
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["agent"] == "documents_agent"
    assert payload["intent"] == "documents"


def test_malformed_firebase_authorization_header_is_rejected():
    response = asyncio.run(
        post_json(
            app,
            "/user",
            {"user_id": "bad-auth", "age": 20, "location": "Delhi", "first_time_voter": True},
            headers={"Authorization": "Token abc"},
        )
    )
    assert response.status_code == 401


def test_invalid_firebase_token_does_not_leak_exception_details():
    response = asyncio.run(
        post_json(
            app,
            "/user",
            {"user_id": "bad-token", "age": 20, "location": "Delhi", "first_time_voter": True},
            headers={"Authorization": "Bearer not-a-real-token"},
        )
    )
    payload = response.json()
    assert response.status_code == 401
    assert payload["detail"] == "Firebase token verification failed"
    assert "not-a-real-token" not in str(payload)


def test_favicon_route_avoids_404_noise():
    response = asyncio.run(get_path(app, "/favicon.ico"))
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/x-icon"


def test_index_has_security_policy_header():
    response = asyncio.run(get_path(app, "/"))
    assert response.status_code == 200
    assert "default-src 'self'" in response.headers["content-security-policy"]
