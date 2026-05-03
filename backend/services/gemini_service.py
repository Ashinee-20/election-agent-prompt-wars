import logging

from google import genai
from google.genai import types

from backend.config import Settings
from backend.models import ChatMessage, UserProfile
from backend.services.timeline_service import generate_timeline

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client | None:
        if self._client:
            return self._client
        try:
            if self.settings.google_genai_use_vertexai:
                self._client = genai.Client(
                    vertexai=True,
                    project=self.settings.google_cloud_project,
                    location=self.settings.google_cloud_location,
                )
            elif self.settings.gemini_api_key:
                self._client = genai.Client(api_key=self.settings.gemini_api_key)
            else:
                return None
            return self._client
        except Exception as exc:
            logger.warning("Gemini client unavailable: %s", exc)
            return None

    def answer(
        self,
        message: str,
        profile: UserProfile | None,
        history: list[ChatMessage],
        agent_instruction: str | None = None,
        use_google_search: bool = False,
        use_google_maps: bool = False,
    ) -> tuple[str, str]:
        client = self._get_client()
        if not client:
            return self._fallback_answer(message, profile), "local-fallback"

        profile_text = profile.model_dump_json() if profile else "No profile saved yet."
        timeline = generate_timeline("current-user", profile)
        history_text = "\n".join(f"{item.role}: {item.content}" for item in history[-8:])
        specialist_instruction = agent_instruction or "Answer as the general election process assistant."
        prompt = f"""
You are a careful, non-partisan Election Assistant. Help users understand election process,
eligibility, documents, registration, polling day, and result timelines. Never endorse a party
or candidate. Encourage users to verify final rules on official election authority websites.
Specialist role: {specialist_instruction}

User profile: {profile_text}
Personalized timeline: {timeline.model_dump_json()}
Recent conversation:
{history_text}

User asks: {message}

Respond in clear steps, with accessible language and any important safety or eligibility caveats.
Keep the answer concise, usually under 180 words, unless the user asks for a long explanation.
If Google Search grounding is available, use it for recent, current, live, latest, result, schedule,
or news questions and mention that election dates and results should be checked with official sources.
"""
        try:
            tools: list[types.Tool] = []
            if use_google_search:
                tools.append(types.Tool(google_search=types.GoogleSearch()))
            if use_google_maps:
                tools.append(types.Tool(google_maps=types.GoogleMaps()))
            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.35,
                    max_output_tokens=2048,
                    tools=tools or None,
                ),
            )
            text = (response.text or "").strip()
            if not text:
                return self._fallback_answer(message, profile), "local-fallback"
            if self._looks_incomplete(text):
                text = f"{text}\n\n{self._fallback_answer(message, profile)}"
            source = "gemini"
            if use_google_search:
                source = "gemini+google-search"
            if use_google_maps:
                source = f"{source}+google-maps"
            return text, source
        except Exception as exc:
            logger.warning("Gemini generation failed: %s", exc)
            return self._fallback_answer(message, profile), "local-fallback"

    def _looks_incomplete(self, text: str) -> bool:
        if len(text) < 120:
            return True
        stripped = text.rstrip()
        if stripped.endswith(("#", ":", "-", "### Your")):
            return True
        return stripped[-1] not in ".!?)]"

    def _fallback_answer(self, message: str, profile: UserProfile | None) -> str:
        lower = message.lower()
        if profile and profile.age < 18:
            return "You are not eligible to vote yet. You can prepare by keeping proof of age, identity, and address ready, then register when you turn 18."
        if "eligible" in lower or "age" in lower:
            return "Most elections require you to be at least 18 and registered in the correct constituency. Add your age and location for tailored guidance."
        if "document" in lower or "id" in lower:
            return "Commonly needed documents include proof of age, identity, address, and any voter registration reference. Always confirm the final list on the official election website."
        if "timeline" in lower:
            return "Your voting journey is: registration, verification, voter list confirmation, voting day, then results. First-time voters should start with registration and document checks."
        return "I can help with eligibility, registration, documents, polling-day steps, and election timelines. Share your age, location, and whether this is your first time voting for a personalized answer."
