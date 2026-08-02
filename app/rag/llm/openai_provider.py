"""OpenAI Chat Completions LLM provider with streaming support."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Sequence

from openai import AsyncOpenAI

from app.core.logging import get_logger
from app.rag.llm.base import LLMProvider

logger = get_logger(__name__)


class OpenAILLMProvider(LLMProvider):
    """
    OpenAI Chat Completions API (stream + non-stream).

    Temperature defaults low to reduce hallucination; callers still must
    supply grounded prompts via PromptBuilder.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        base_url: str | None = None,
    ) -> None:
        self._model = model
        self._temperature = temperature
        kwargs: dict[str, str] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)

    @property
    def model_name(self) -> str:
        return self._model

    async def stream_chat(
        self,
        messages: Sequence[dict[str, str]],
    ) -> AsyncIterator[str]:
        started = time.perf_counter()
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=list(messages),  # type: ignore[arg-type]
            temperature=self._temperature,
            stream=True,
        )
        token_count = 0
        async for event in stream:
            if not event.choices:
                continue
            delta = event.choices[0].delta.content
            if delta:
                token_count += 1
                yield delta

        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "llm_stream_completed",
            model=self._model,
            latency_ms=round(elapsed_ms, 2),
            token_fragments=token_count,
        )

    async def complete_chat(
        self,
        messages: Sequence[dict[str, str]],
    ) -> str:
        started = time.perf_counter()
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=list(messages),  # type: ignore[arg-type]
            temperature=self._temperature,
            stream=False,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        content = response.choices[0].message.content or ""
        logger.info(
            "llm_complete_completed",
            model=self._model,
            latency_ms=round(elapsed_ms, 2),
        )
        return content
