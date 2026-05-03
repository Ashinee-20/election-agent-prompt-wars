from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class UserProfile(BaseModel):
    user_id: str = Field(default="demo-user", min_length=1, max_length=120)
    age: int = Field(ge=0, le=130)
    location: str = Field(min_length=2, max_length=120)
    first_time_voter: bool = True
    language: str = Field(default="English", max_length=40)

    @field_validator("location", "language")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()


class UserProfileResponse(BaseModel):
    saved: bool
    profile: UserProfile
    guidance: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1200)
    user_id: str = Field(default="demo-user", min_length=1, max_length=120)
    profile: UserProfile | None = None

    @field_validator("message")
    @classmethod
    def trim_message(cls, value: str) -> str:
        return value.strip()


class ChatResponse(BaseModel):
    response: str
    user_id: str
    history: list[ChatMessage]
    data_source: str


class TimelineStep(BaseModel):
    id: str
    title: str
    description: str
    status: Literal["now", "next", "later", "not_eligible"]
    actions: list[str]


class TimelineResponse(BaseModel):
    user_id: str
    generated_for: UserProfile | None
    steps: list[TimelineStep]
    note: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
