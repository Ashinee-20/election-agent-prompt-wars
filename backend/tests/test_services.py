import importlib.metadata

from backend.config import Settings
from backend.models import ChatMessage, UserProfile
from backend.services.adk_agent import ElectionAdkAgent
from backend.services.firestore_service import FirestoreService
from backend.services.gemini_service import GeminiService
from backend.services.maps_service import mock_polling_centers
from backend.services.timeline_service import eligibility_guidance, generate_timeline


def test_firestore_memory_fallback_saves_profile_and_chat(monkeypatch):
    service = FirestoreService(Settings())
    monkeypatch.setattr(service, "_get_client", lambda: None)
    profile = UserProfile(user_id="memory-user", age=19, location="Jaipur", first_time_voter=True)

    saved_remotely = service.save_profile(profile)
    service.append_chat("memory-user", "user", "Hello")
    service.append_chat("memory-user", "assistant", "Hi")

    assert saved_remotely is False
    assert service.get_profile("memory-user") == profile
    assert [message.role for message in service.get_chat_history("memory-user")] == ["user", "assistant"]


def test_firestore_history_limit_in_memory(monkeypatch):
    service = FirestoreService(Settings())
    monkeypatch.setattr(service, "_get_client", lambda: None)
    for index in range(5):
        service.append_chat("limit-user", "user", f"message {index}")

    history = service.get_chat_history("limit-user", limit=2)
    assert [message.content for message in history] == ["message 3", "message 4"]


def test_gemini_fallback_handles_documents_question():
    service = GeminiService(Settings(gemini_api_key=None))
    answer, source = service.answer("What documents do I need?", None, [])
    assert source == "local-fallback"
    assert "proof" in answer.lower()


def test_gemini_fallback_handles_underage_profile():
    profile = UserProfile(user_id="young", age=15, location="Lucknow", first_time_voter=True)
    service = GeminiService(Settings(gemini_api_key=None))
    answer, source = service.answer("Can I vote?", profile, [])
    assert source == "local-fallback"
    assert "not eligible" in answer.lower()


def test_adk_agent_delegates_to_gemini_fallback():
    agent = ElectionAdkAgent(Settings(gemini_api_key=None))
    response, source = agent.run("Show timeline", None, [])
    assert response
    assert source == "local-fallback"


def test_adk_detection_uses_package_metadata(monkeypatch):
    agent = ElectionAdkAgent(Settings(gemini_api_key=None))

    def fake_import(name, *args, **kwargs):
        if name == "google.adk":
            raise ImportError("namespace unavailable")
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(importlib.metadata, "version", lambda package: "0.1.0" if package == "google-adk" else "0")
    assert agent._detect_adk() is True


def test_timeline_without_profile_prompts_personalization():
    timeline = generate_timeline("anonymous", None)
    assert timeline.generated_for is None
    assert "Add your profile" in timeline.note
    assert len(timeline.steps) == 4


def test_first_time_voter_gets_registration_now():
    profile = UserProfile(user_id="first", age=20, location="Delhi", first_time_voter=True)
    timeline = generate_timeline("first", profile)
    assert timeline.steps[0].status == "now"
    assert "registration" in timeline.steps[0].title.lower()


def test_eligibility_guidance_for_exactly_18():
    profile = UserProfile(user_id="adult", age=18, location="Delhi", first_time_voter=True)
    assert "eligible" in eligibility_guidance(profile).lower()


def test_mock_polling_centers_include_profile_location():
    profile = UserProfile(user_id="maps", age=44, location="Mysuru", first_time_voter=False)
    centers = mock_polling_centers(profile)
    assert len(centers) == 2
    assert "Mysuru" in centers[0]["address"]


def test_gemini_prompt_accepts_existing_history():
    service = GeminiService(Settings(gemini_api_key=None))
    history = [ChatMessage(role="user", content="Earlier question", created_at="2026-05-03T00:00:00+00:00")]
    answer, source = service.answer("Show my timeline", None, history)
    assert source == "local-fallback"
    assert "journey" in answer.lower()


def test_gemini_incomplete_response_detection():
    service = GeminiService(Settings(gemini_api_key=None))
    assert service._looks_incomplete("Here is a plan:\n\n### Your") is True
    assert service._looks_incomplete("This complete response has enough detail to be useful. " * 4) is False
