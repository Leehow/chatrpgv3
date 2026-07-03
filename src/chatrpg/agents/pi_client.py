from __future__ import annotations

from typing import Any

import orjson
from openai import AsyncOpenAI
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

        client = AsyncOpenAI(
            api_key=self._settings.pi_api_key,
            base_url=self._settings.pi_base_url,
        )
        response = await client.chat.completions.create(
            model=self._settings.pi_model,
            messages=[message.model_dump(mode="json") for message in _json_messages(messages, json_schema)],
            stream=False,
            response_format={"type": "json_object"},
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}, "metadata": {"trace_id": trace_id, "task": task}},
        )
        return _extract_json_object(response)


def _json_messages(messages: list[PiMessage], json_schema: dict[str, Any]) -> list[PiMessage]:
    schema_text = orjson.dumps(json_schema).decode("utf-8")
    return [
        PiMessage(
            role="system",
            content=f"Return only valid json. The json object must conform to this JSON Schema: {schema_text}",
        ),
        *messages,
    ]


def _extract_json_object(data: Any) -> dict[str, Any]:
    if isinstance(data, dict) and "choices" not in data:
        return data
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    if isinstance(data, dict):
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    value = message.get("content")
                    if isinstance(value, str):
                        parsed = orjson.loads(value)
                        if isinstance(parsed, dict):
                            return parsed
    raise TypeError("Pi response did not contain a JSON object")
