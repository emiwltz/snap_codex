"""Tests for OpenRouter request payload construction."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from src.api_client import OpenRouterClient


def test_generate_omits_none_sampling_parameters() -> None:
    captured_payload: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content.decode("utf-8")))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            },
        )

    async def run_call() -> None:
        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport)
        client = OpenRouterClient(api_key="test-key", http_client=http_client)
        async with client:
            result = await client.generate(
                model_id="openai/gpt-5.2",
                messages=[{"role": "user", "content": "hello"}],
                temperature=None,
                top_p=None,
            )
        assert result.error is None

    asyncio.run(run_call())

    assert captured_payload["model"] == "openai/gpt-5.2"
    assert "temperature" not in captured_payload
    assert "top_p" not in captured_payload
    assert captured_payload["max_tokens"] == 2048
