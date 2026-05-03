import pytest
from pydantic import ValidationError

from backend.models import ChatRequest, UserProfile


def test_profile_trims_text_fields():
    profile = UserProfile(user_id="u1", age=18, location="  Kochi  ", language="  English  ")
    assert profile.location == "Kochi"
    assert profile.language == "English"


def test_profile_rejects_unrealistic_age():
    with pytest.raises(ValidationError):
        UserProfile(user_id="u1", age=131, location="Delhi")


def test_profile_rejects_missing_location():
    with pytest.raises(ValidationError):
        UserProfile(user_id="u1", age=18, location="")


def test_chat_message_is_trimmed():
    request = ChatRequest(user_id="u1", message="  How do I vote?  ")
    assert request.message == "How do I vote?"


def test_chat_rejects_overlong_message():
    with pytest.raises(ValidationError):
        ChatRequest(user_id="u1", message="x" * 1201)
