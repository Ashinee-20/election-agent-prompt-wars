import logging
from typing import Any

from google.api_core.exceptions import GoogleAPIError
from google.cloud import firestore

from backend.config import Settings
from backend.models import ChatMessage, UserProfile, utc_now

logger = logging.getLogger(__name__)


class FirestoreService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: firestore.Client | None = None
        self._memory_profiles: dict[str, dict[str, Any]] = {}
        self._memory_history: dict[str, list[dict[str, Any]]] = {}

    @property
    def enabled(self) -> bool:
        return self._get_client() is not None

    def _get_client(self) -> firestore.Client | None:
        if self._client:
            return self._client
        try:
            project = self.settings.firebase_project_id or self.settings.google_cloud_project
            self._client = firestore.Client(project=project) if project else firestore.Client()
            return self._client
        except Exception as exc:
            logger.info("Firestore unavailable, using in-memory fallback: %s", exc)
            return None

    def _collection(self, name: str) -> str:
        return f"{self.settings.firestore_collection_prefix}_{name}"

    def save_profile(self, profile: UserProfile) -> bool:
        payload = profile.model_dump()
        payload["updated_at"] = utc_now()
        client = self._get_client()
        if not client:
            self._memory_profiles[profile.user_id] = payload
            return False
        try:
            client.collection(self._collection("users")).document(profile.user_id).set(payload, merge=True)
            return True
        except GoogleAPIError as exc:
            logger.warning("Firestore profile save failed: %s", exc)
            self._memory_profiles[profile.user_id] = payload
            return False

    def get_profile(self, user_id: str) -> UserProfile | None:
        client = self._get_client()
        if not client:
            payload = self._memory_profiles.get(user_id)
            return UserProfile(**payload) if payload else None
        try:
            snapshot = client.collection(self._collection("users")).document(user_id).get()
            return UserProfile(**snapshot.to_dict()) if snapshot.exists else None
        except GoogleAPIError as exc:
            logger.warning("Firestore profile read failed: %s", exc)
            payload = self._memory_profiles.get(user_id)
            return UserProfile(**payload) if payload else None

    def append_chat(self, user_id: str, role: str, content: str) -> None:
        payload = {"role": role, "content": content, "created_at": utc_now()}
        client = self._get_client()
        if not client:
            self._memory_history.setdefault(user_id, []).append(payload)
            return
        try:
            client.collection(self._collection("chats")).document(user_id).collection("messages").add(payload)
        except GoogleAPIError as exc:
            logger.warning("Firestore chat save failed: %s", exc)
            self._memory_history.setdefault(user_id, []).append(payload)

    def get_chat_history(self, user_id: str, limit: int = 12) -> list[ChatMessage]:
        client = self._get_client()
        if not client:
            rows = self._memory_history.get(user_id, [])[-limit:]
            return [ChatMessage(**row) for row in rows]
        try:
            query = (
                client.collection(self._collection("chats"))
                .document(user_id)
                .collection("messages")
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
            rows = [ChatMessage(**doc.to_dict()) for doc in query.stream()]
            return list(reversed(rows))
        except GoogleAPIError as exc:
            logger.warning("Firestore chat read failed: %s", exc)
            rows = self._memory_history.get(user_id, [])[-limit:]
            return [ChatMessage(**row) for row in rows]
