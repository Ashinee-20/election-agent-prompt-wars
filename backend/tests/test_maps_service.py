import asyncio

import httpx

from backend.config import Settings
from backend.models import UserProfile
from backend.services.maps_service import lookup_polling_centers


def test_maps_lookup_returns_clear_missing_key_mode():
    profile = UserProfile(user_id="maps-test", age=30, location="Delhi", first_time_voter=False)
    result = asyncio.run(lookup_polling_centers(profile, Settings(google_maps_api_key=None)))
    assert result["mode"] == "mock-google-maps-api-key-missing"
    assert "GOOGLE_MAPS_API_KEY" in result["note"]


def test_maps_lookup_uses_places_api_when_key_exists(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{"name": "Official School Booth", "formatted_address": "Main Road", "place_id": "abc"}]}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, params):
            captured["url"] = url
            captured["params"] = params
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    profile = UserProfile(user_id="maps-live", age=30, location="Pune", first_time_voter=False)
    result = asyncio.run(lookup_polling_centers(profile, Settings(google_maps_api_key="test-key")))

    assert result["mode"] == "google-places-api"
    assert captured["params"]["key"] == "test-key"
    assert "Pune" in captured["params"]["query"]
