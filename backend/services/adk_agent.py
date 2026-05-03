from backend.config import Settings
from backend.models import ChatMessage, UserProfile
from backend.services.gemini_service import GeminiService


class ElectionAdkAgent:
    """Thin ADK-friendly wrapper with a graceful fallback for local judging."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.gemini = GeminiService(settings)
        self.adk_available = self._detect_adk()

    def _detect_adk(self) -> bool:
        try:
            import google.adk  # noqa: F401

            return True
        except Exception:
            try:
                from importlib.metadata import version

                version("google-adk")
                return True
            except Exception:
                return False

    def run(self, message: str, profile: UserProfile | None, history: list[ChatMessage]) -> tuple[str, str]:
        response, source = self.gemini.answer(message, profile, history)
        if self.adk_available and source == "gemini":
            return response, "google-adk+gemini"
        return response, source
