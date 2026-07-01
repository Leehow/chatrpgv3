from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel

from chatrpg.config import Settings


class PiMessage(BaseModel):
    role: str
    content: str


class PiClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    async def complete_json(
        self,
        *,
        task: str,
        messages: list[PiMessage],
        json_schema: dict[str, Any],
        trace_id: str,
    ) -> dict[str, Any]:
        if not self._settings.pi_base_url or not self._settings.pi_api_key:
            raise RuntimeError("Pi client is not configured.")

        payload = {
            "model": self._settings.pi_model,
            "messages": [message.model_dump(mode="json") for message in messages],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": task, "schema": json_schema, "strict": True},
            },
            "metadata": {"trace_id": trace_id, "task": task},
        }
        headers = {"Authorization": f"Bearer {self._settings.pi_api_key}"}
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(self._settings.pi_base_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        if isinstance(data, dict):
            return data
        raise TypeError("Pi response must be a JSON object")
