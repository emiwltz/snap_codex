"""Async OpenRouter client with protocol-specific retry policy."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

LOGGER = logging.getLogger(__name__)

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT_RETRY_DELAY_SECONDS = 30
SERVER_RETRY_DELAY_SECONDS = 60
RATE_LIMIT_BACKOFF_SECONDS = [60, 120, 240]
EMPTY_RESPONSE_RETRIES = 1


@dataclass
class ApiErrorInfo:
    """Structured API error metadata."""

    error_type: str
    message: str
    status_code: int | None = None
    attempts: int = 1


@dataclass
class ApiCallResult:
    """Result of one OpenRouter generation call."""

    content: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    response_time_ms: int | None
    status_code: int | None
    error: ApiErrorInfo | None


class OpenRouterClient:
    """OpenRouter async client with built-in retry/backoff and rate limiting."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str = OPENROUTER_ENDPOINT,
        min_delay_seconds: float = 1.0,
        timeout_seconds: float = 60.0,
        sleep_fn: Callable[[float], Any] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.endpoint = endpoint
        self.min_delay_seconds = min_delay_seconds
        self.timeout_seconds = timeout_seconds
        self._sleep = sleep_fn or asyncio.sleep
        self._provided_client = http_client
        self._client: httpx.AsyncClient | None = http_client
        self._last_call_ts = 0.0
        self._rate_lock = asyncio.Lock()

    async def __aenter__(self) -> OpenRouterClient:
        await self.open()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, exc_tb: Any) -> None:
        await self.close()

    async def open(self) -> None:
        """Initialize underlying AsyncClient if needed."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)

    async def close(self) -> None:
        """Close underlying AsyncClient if it is owned by this instance."""
        if self._client is not None and self._provided_client is None:
            await self._client.aclose()
            self._client = None

    async def _respect_min_delay(self) -> None:
        """Ensure minimum delay between API calls."""
        async with self._rate_lock:
            now = time.monotonic()
            elapsed = now - self._last_call_ts
            if elapsed < self.min_delay_seconds:
                await self._sleep(self.min_delay_seconds - elapsed)
            self._last_call_ts = time.monotonic()

    async def generate(
        self,
        model_id: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        extra_body: dict[str, Any] | None = None,
    ) -> ApiCallResult:
        """Run one generation call with protocol-specific retries.

        Args:
            model_id: OpenRouter model identifier.
            messages: OpenAI-compatible chat messages.
            temperature: Sampling temperature.
            max_tokens: Max completion tokens.
            top_p: Top-p sampling parameter.
            extra_body: Additional provider parameters.

        Returns:
            ApiCallResult containing either content or structured error info.
        """
        if not self.api_key:
            return ApiCallResult(
                content=None,
                prompt_tokens=None,
                completion_tokens=None,
                response_time_ms=None,
                status_code=None,
                error=ApiErrorInfo(
                    error_type="missing_api_key",
                    message="OPENROUTER_API_KEY is not configured.",
                ),
            )

        await self.open()
        assert self._client is not None

        timeout_attempts = 0
        server_attempts = 0
        rate_attempts = 0
        empty_attempts = 0
        network_attempts = 0
        total_attempts = 0

        while True:
            total_attempts += 1
            await self._respect_min_delay()

            payload: dict[str, Any] = {
                "model": model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
            }
            if extra_body:
                payload.update(extra_body)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            started = time.perf_counter()
            try:
                response = await self._client.post(
                    self.endpoint, json=payload, headers=headers
                )
            except httpx.TimeoutException as exc:
                timeout_attempts += 1
                if timeout_attempts >= 3:
                    return ApiCallResult(
                        content=None,
                        prompt_tokens=None,
                        completion_tokens=None,
                        response_time_ms=None,
                        status_code=None,
                        error=ApiErrorInfo(
                            error_type="timeout",
                            message=str(exc),
                            attempts=timeout_attempts,
                        ),
                    )
                LOGGER.warning(
                    "Timeout for model=%s, retry %d/3 in %ss",
                    model_id,
                    timeout_attempts,
                    TIMEOUT_RETRY_DELAY_SECONDS,
                )
                await self._sleep(TIMEOUT_RETRY_DELAY_SECONDS)
                continue
            except httpx.RequestError as exc:
                network_attempts += 1
                if network_attempts >= 3:
                    return ApiCallResult(
                        content=None,
                        prompt_tokens=None,
                        completion_tokens=None,
                        response_time_ms=None,
                        status_code=None,
                        error=ApiErrorInfo(
                            error_type="network_error",
                            message=str(exc),
                            attempts=network_attempts,
                        ),
                    )
                LOGGER.warning(
                    "Network error for model=%s, retry %d/3 in %ss",
                    model_id,
                    network_attempts,
                    SERVER_RETRY_DELAY_SECONDS,
                )
                await self._sleep(SERVER_RETRY_DELAY_SECONDS)
                continue

            response_time_ms = int((time.perf_counter() - started) * 1000)
            status_code = response.status_code

            if status_code == 429:
                rate_attempts += 1
                if rate_attempts > len(RATE_LIMIT_BACKOFF_SECONDS):
                    return ApiCallResult(
                        content=None,
                        prompt_tokens=None,
                        completion_tokens=None,
                        response_time_ms=response_time_ms,
                        status_code=status_code,
                        error=ApiErrorInfo(
                            error_type="rate_limit",
                            message=response.text,
                            status_code=status_code,
                            attempts=rate_attempts,
                        ),
                    )
                wait_seconds = RATE_LIMIT_BACKOFF_SECONDS[rate_attempts - 1]
                LOGGER.warning(
                    "Rate limit for model=%s, retry %d/%d in %ss",
                    model_id,
                    rate_attempts,
                    len(RATE_LIMIT_BACKOFF_SECONDS),
                    wait_seconds,
                )
                await self._sleep(wait_seconds)
                continue

            if 500 <= status_code < 600:
                server_attempts += 1
                if server_attempts >= 3:
                    return ApiCallResult(
                        content=None,
                        prompt_tokens=None,
                        completion_tokens=None,
                        response_time_ms=response_time_ms,
                        status_code=status_code,
                        error=ApiErrorInfo(
                            error_type="server_error",
                            message=response.text,
                            status_code=status_code,
                            attempts=server_attempts,
                        ),
                    )
                LOGGER.warning(
                    "Server error %s for model=%s, retry %d/3 in %ss",
                    status_code,
                    model_id,
                    server_attempts,
                    SERVER_RETRY_DELAY_SECONDS,
                )
                await self._sleep(SERVER_RETRY_DELAY_SECONDS)
                continue

            if 400 <= status_code < 500:
                return ApiCallResult(
                    content=None,
                    prompt_tokens=None,
                    completion_tokens=None,
                    response_time_ms=response_time_ms,
                    status_code=status_code,
                    error=ApiErrorInfo(
                        error_type="client_error",
                        message=response.text,
                        status_code=status_code,
                        attempts=total_attempts,
                    ),
                )

            try:
                body = response.json()
            except ValueError:
                return ApiCallResult(
                    content=None,
                    prompt_tokens=None,
                    completion_tokens=None,
                    response_time_ms=response_time_ms,
                    status_code=status_code,
                    error=ApiErrorInfo(
                        error_type="invalid_json",
                        message="Response body is not valid JSON.",
                        status_code=status_code,
                        attempts=total_attempts,
                    ),
                )

            content = self._extract_content(body)
            usage = body.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")

            if not content or not str(content).strip():
                if empty_attempts < EMPTY_RESPONSE_RETRIES:
                    empty_attempts += 1
                    LOGGER.warning(
                        "Empty response for model=%s, retry %d/%d",
                        model_id,
                        empty_attempts,
                        EMPTY_RESPONSE_RETRIES,
                    )
                    continue
                return ApiCallResult(
                    content=None,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    response_time_ms=response_time_ms,
                    status_code=status_code,
                    error=ApiErrorInfo(
                        error_type="empty_response",
                        message="OpenRouter returned an empty response.",
                        status_code=status_code,
                        attempts=total_attempts,
                    ),
                )

            return ApiCallResult(
                content=str(content),
                prompt_tokens=int(prompt_tokens) if prompt_tokens is not None else None,
                completion_tokens=(
                    int(completion_tokens) if completion_tokens is not None else None
                ),
                response_time_ms=response_time_ms,
                status_code=status_code,
                error=None,
            )

    @staticmethod
    def _extract_content(body: dict[str, Any]) -> str | None:
        """Extract text content from OpenRouter/OpenAI-compatible payload."""
        choices = body.get("choices")
        if not choices:
            return None
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not message:
            return None
        content = message.get("content")
        if isinstance(content, list):
            fragments: list[str] = []
            for chunk in content:
                if isinstance(chunk, dict) and chunk.get("type") == "text":
                    fragments.append(str(chunk.get("text", "")))
            return "".join(fragments)
        if content is None:
            return None
        return str(content)
