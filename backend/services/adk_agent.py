import os
from dataclasses import dataclass
from typing import Literal

from backend.config import Settings
from backend.models import ChatMessage, UserProfile
from backend.services.gemini_service import GeminiService

Intent = Literal["eligibility", "timeline", "documents", "polling", "realtime", "general"]


@dataclass(frozen=True)
class AgentResult:
    response: str
    source: str
    agent: str
    intent: Intent


def search_recent_election_info(query: str) -> dict[str, str]:
    """ADK tool: answer realtime election questions with Gemini Google Search grounding."""
    settings = Settings(
        google_genai_use_vertexai=os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true",
        google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        google_cloud_location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    )
    answer, source = GeminiService(settings).answer(
        message=query,
        profile=None,
        history=[],
        agent_instruction="Use Google Search grounding to answer recent election news, results, and schedule questions.",
        use_google_search=True,
    )
    return {"answer": answer, "source": source}


def google_maps_polling_guidance(location: str) -> dict[str, str]:
    """ADK tool: describe how Maps/Places lookup should be used for polling-place discovery."""
    if os.getenv("GOOGLE_MAPS_API_KEY"):
        return {
            "status": "available",
            "guidance": f"Use Google Places Text Search for election polling stations near {location}.",
        }
    return {
        "status": "api_key_missing",
        "guidance": "Google Maps Platform APIs are enabled. Set GOOGLE_MAPS_API_KEY to use live Places lookup.",
    }


def build_actual_adk_agents(settings: Settings):
    """Build real ADK LlmAgent objects when google.adk is available in the runtime."""
    try:
        from google.adk.agents import LlmAgent
        from google.adk.apps.app import App
        from google.adk.models import Gemini
        from google.genai.types import HttpRetryOptions
    except Exception:
        return None

    retry_options = HttpRetryOptions(initial_delay=1, max_delay=3, attempts=10)
    model = Gemini(model=settings.gemini_model, retry_options=retry_options)

    eligibility_agent = LlmAgent(
        model=model,
        name="eligibility_agent",
        description="Determines voter eligibility and next steps.",
        instruction=EligibilityAgent.instruction,
    )
    timeline_agent = LlmAgent(
        model=model,
        name="timeline_agent",
        description="Builds personalized election timelines.",
        instruction=TimelineAgent.instruction,
    )
    documents_agent = LlmAgent(
        model=model,
        name="documents_agent",
        description="Explains accepted voting and registration documents.",
        instruction=DocumentsAgent.instruction,
    )
    polling_agent = LlmAgent(
        model=model,
        name="polling_agent",
        description="Helps with polling booth and voting-day location questions.",
        instruction=PollingAgent.instruction,
        tools=[google_maps_polling_guidance],
    )
    realtime_agent = LlmAgent(
        model=model,
        name="realtime_election_agent",
        description="Uses Google Search grounding for recent election questions.",
        instruction=RealtimeElectionAgent.instruction,
        tools=[search_recent_election_info],
    )
    general_agent = LlmAgent(
        model=model,
        name="general_process_agent",
        description="Explains the general voting process.",
        instruction=ElectionSpecialistAgent.instruction,
    )

    root_agent = LlmAgent(
        model=model,
        name="election_orchestrator_agent",
        description="Routes election questions to specialist agents by user intent.",
        instruction=(
            "Classify the user's election question and transfer to the best specialist: "
            "eligibility_agent, timeline_agent, documents_agent, polling_agent, "
            "realtime_election_agent, or general_process_agent."
        ),
        sub_agents=[
            eligibility_agent,
            timeline_agent,
            documents_agent,
            polling_agent,
            realtime_agent,
            general_agent,
        ],
    )

    return App(name="election_assistant_adk_app", root_agent=root_agent)


class ElectionSpecialistAgent:
    name = "general_process_agent"
    intent: Intent = "general"
    instruction = "Explain election processes in neutral, beginner-friendly steps."
    use_google_search = False
    use_google_maps = False

    def __init__(self, gemini: GeminiService):
        self.gemini = gemini

    def run(self, message: str, profile: UserProfile | None, history: list[ChatMessage]) -> AgentResult:
        response, source = self.gemini.answer(
            message=message,
            profile=profile,
            history=history,
            agent_instruction=self.instruction,
            use_google_search=self.use_google_search,
            use_google_maps=self.use_google_maps,
        )
        return AgentResult(response=response, source=source, agent=self.name, intent=self.intent)


class EligibilityAgent(ElectionSpecialistAgent):
    name = "eligibility_agent"
    intent: Intent = "eligibility"
    instruction = "Focus on voting eligibility, age, registration status, and what the user can do next."


class TimelineAgent(ElectionSpecialistAgent):
    name = "timeline_agent"
    intent: Intent = "timeline"
    instruction = "Focus on step-by-step election timelines: registration, verification, polling, and results."


class DocumentsAgent(ElectionSpecialistAgent):
    name = "documents_agent"
    intent: Intent = "documents"
    instruction = "Focus on required documents, identity proof, address proof, voter ID, and official verification."


class PollingAgent(ElectionSpecialistAgent):
    name = "polling_agent"
    intent: Intent = "polling"
    instruction = "Focus on polling booth lookup, voting-day preparation, accessibility, queues, and route planning."
    use_google_maps = True


class RealtimeElectionAgent(ElectionSpecialistAgent):
    name = "realtime_election_agent"
    intent: Intent = "realtime"
    instruction = (
        "Answer recent, latest, current, completed, upcoming, result, schedule, and news questions. "
        "Use Google Search grounding and clearly separate verified facts from guidance."
    )
    use_google_search = True


class ElectionOrchestratorAgent:
    """Routes each user turn to a specialist election agent."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.gemini = GeminiService(settings)
        self.adk_available = self._detect_adk()
        self.adk_app = build_actual_adk_agents(settings)
        self.agents: dict[Intent, ElectionSpecialistAgent] = {
            "eligibility": EligibilityAgent(self.gemini),
            "timeline": TimelineAgent(self.gemini),
            "documents": DocumentsAgent(self.gemini),
            "polling": PollingAgent(self.gemini),
            "realtime": RealtimeElectionAgent(self.gemini),
            "general": ElectionSpecialistAgent(self.gemini),
        }

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

    def classify_intent(self, message: str) -> Intent:
        text = message.lower()
        realtime_terms = (
            "recent",
            "latest",
            "current",
            "today",
            "yesterday",
            "news",
            "result",
            "results",
            "won",
            "winner",
            "completed",
            "upcoming",
            "schedule",
            "date",
            "2026",
            "2025",
        )
        if any(term in text for term in realtime_terms):
            return "realtime"
        if any(term in text for term in ("eligible", "eligibility", "age", "under 18", "can i vote")):
            return "eligibility"
        if any(term in text for term in ("timeline", "steps", "process", "flow", "when do i")):
            return "timeline"
        if any(term in text for term in ("document", "documents", "id", "proof", "voter id", "address proof")):
            return "documents"
        if any(term in text for term in ("polling", "booth", "center", "centre", "nearby", "map", "route", "where do i vote")):
            return "polling"
        return "general"

    def run(self, message: str, profile: UserProfile | None, history: list[ChatMessage]) -> AgentResult:
        intent = self.classify_intent(message)
        return self.agents[intent].run(message, profile, history)


# Backwards-compatible name used by the FastAPI app.
ElectionAdkAgent = ElectionOrchestratorAgent
