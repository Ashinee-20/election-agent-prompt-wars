from backend.models import TimelineResponse, TimelineStep, UserProfile


def eligibility_guidance(profile: UserProfile) -> str:
    if profile.age < 18:
        years = 18 - profile.age
        suffix = "year" if years == 1 else "years"
        return f"You are not eligible to vote yet. You can prepare documents and register when you turn 18 in {years} {suffix}."
    if profile.first_time_voter:
        return "You are eligible. Start with voter registration, document readiness, and local verification."
    return "You are eligible. Confirm your voter record, polling details, and voting-day documents."


def generate_timeline(user_id: str, profile: UserProfile | None) -> TimelineResponse:
    if profile and profile.age < 18:
        steps = [
            TimelineStep(
                id="prepare",
                title="Prepare Before Eligibility",
                description="Collect proof of age, identity, and residence so registration is easy when you turn 18.",
                status="not_eligible",
                actions=["Check accepted ID documents", "Keep address proof updated", "Set a reminder near your 18th birthday"],
            ),
            TimelineStep(
                id="register_at_18",
                title="Register At 18",
                description="Submit your voter registration form through the official election authority for your location.",
                status="later",
                actions=["Use official government portals only", "Review all details before submitting"],
            ),
        ]
        note = eligibility_guidance(profile)
    else:
        first_time = profile.first_time_voter if profile else True
        steps = [
            TimelineStep(
                id="registration",
                title="Registration",
                description="Create or update your voter record with accurate personal and address information.",
                status="now" if first_time else "next",
                actions=["Submit registration form", "Upload or carry valid documents", "Save your reference number"],
            ),
            TimelineStep(
                id="verification",
                title="Verification",
                description="Election officials verify your identity, age, residence, and polling area assignment.",
                status="next",
                actions=["Track application status", "Correct errors quickly", "Confirm your name appears on the voter list"],
            ),
            TimelineStep(
                id="polling",
                title="Voting Day",
                description="Go to your assigned polling center during official hours with accepted identification.",
                status="later",
                actions=["Check polling booth location", "Carry required ID", "Follow queue and ballot instructions"],
            ),
            TimelineStep(
                id="results",
                title="Result Timeline",
                description="Results are declared after counting and official verification by the election authority.",
                status="later",
                actions=["Follow official result channels", "Avoid unverified claims", "Save receipts where applicable"],
            ),
        ]
        if profile and not profile.first_time_voter:
            steps[0].description = "Review your existing voter record and update address or name changes if needed."
            steps[0].actions = ["Confirm voter list entry", "Update changed details", "Check assigned polling center"]
        note = eligibility_guidance(profile) if profile else "Add your profile for a personalized timeline."

    return TimelineResponse(user_id=user_id, generated_for=profile, steps=steps, note=note)
