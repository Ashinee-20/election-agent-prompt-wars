from backend.models import UserProfile


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
