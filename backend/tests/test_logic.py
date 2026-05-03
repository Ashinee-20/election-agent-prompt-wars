import asyncio

from backend.main import app
from backend.models import UserProfile
from backend.services.timeline_service import eligibility_guidance, generate_timeline
from backend.tests.utils import post_json


def test_underage_guidance_is_clear():
    profile = UserProfile(user_id="u1", age=16, location="Mumbai", first_time_voter=True)
    assert "not eligible" in eligibility_guidance(profile).lower()
    timeline = generate_timeline("u1", profile)
    assert timeline.steps[0].status == "not_eligible"


def test_returning_voter_skips_beginner_registration_copy():
    profile = UserProfile(user_id="u2", age=30, location="Bengaluru", first_time_voter=False)
    timeline = generate_timeline("u2", profile)
    assert "existing voter record" in timeline.steps[0].description


def test_chat_endpoint_returns_response():
    response = asyncio.run(
        post_json(
            app,
            "/chat",
            {
                "user_id": "test-user",
                "message": "Am I eligible?",
                "profile": {
                    "user_id": "test-user",
                    "age": 18,
                    "location": "Delhi",
                    "first_time_voter": True,
                },
            },
        )
    )
    assert response.status_code == 200
    assert response.json()["response"]
