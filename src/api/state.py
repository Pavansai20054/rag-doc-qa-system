from typing import Any


class ConversationState:
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = {}

    def get(self, conversation_id: str) -> list[dict[str, Any]]:
        return self._store.get(conversation_id, [])

    def append(self, conversation_id: str, message: dict[str, Any]) -> None:
        self._store.setdefault(conversation_id, []).append(message)


CONVERSATIONS = ConversationState()
