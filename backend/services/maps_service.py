import httpx

from backend.config import Settings
from backend.models import UserProfile


async def lookup_polling_centers(profile: UserProfile | None, settings: Settings) -> dict[str, object]:
    if settings.google_maps_api_key:
        location = profile.location if profile else "near me"
        query = f"polling station near {location}"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={"query": query, "key": settings.google_maps_api_key},
            )
            response.raise_for_status()
        payload = response.json()
        centers = [
            {
                "name": item.get("name", "Polling location"),
                "address": item.get("formatted_address", "Address unavailable"),
                "distance": "Check Maps",
                "maps_place_id": item.get("place_id"),
            }
            for item in payload.get("results", [])[:5]
        ]
        return {"centers": centers, "mode": "google-places-api"}

    return {
        "centers": mock_polling_centers(profile),
        "mode": "mock-google-maps-api-key-missing",
        "note": "Google Maps Platform APIs are enabled; set GOOGLE_MAPS_API_KEY to use live Places lookup.",
    }


def mock_polling_centers(profile: UserProfile | None) -> list[dict[str, str]]:
    location = profile.location if profile else "your area"
    return [
        {
            "name": "Central Community Hall",
            "address": f"Main Road, {location}",
            "distance": "1.2 km",
        },
        {
            "name": "Government High School",
            "address": f"School Street, {location}",
            "distance": "2.4 km",
        },
    ]
