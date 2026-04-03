from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

import anthropic
import openai
from google import genai
from google.genai import types as genai_types
from google.genai import errors as genai_errors
from huggingface_hub import AsyncInferenceClient


class QuotaExhaustedError(Exception):
    """Raised when the LLM provider's quota is exhausted and retries won't help."""
    pass


class ServiceUnavailableError(Exception):
    """Raised when the LLM service is unavailable after all retries."""
    pass

@dataclass
class LLMResponse:
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    raw: Any = None  # provider-specific response object


class LLMClient(Protocol):
    """General interface for any LLM."""

    async def generate(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse: ...


class AnthropicClient(LLMClient):
    """Claude-backed LLM client with tool use support."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_tokens: int = 1024,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )

    async def generate(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        response = await self.client.messages.create(**kwargs)

        # Parse response content blocks
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        return LLMResponse(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            raw=response,
        )


# ---------------------------------------------------------------------------
# Gemini implementation
# ---------------------------------------------------------------------------

def _anthropic_tools_to_gemini(tools: list[dict[str, Any]]) -> list[genai_types.Tool]:
    """Convert Anthropic-format tool definitions to Gemini FunctionDeclarations."""
    declarations = []
    for tool in tools:
        # Anthropic uses "input_schema", Gemini uses "parameters" (JSON Schema)
        schema = tool.get("input_schema", {})
        declarations.append(genai_types.FunctionDeclaration(
            name=tool["name"],
            description=tool.get("description", ""),
            parameters=schema,
        ))
    return [genai_types.Tool(function_declarations=declarations)]


def _anthropic_messages_to_gemini(
    messages: list[dict[str, Any]],
) -> list[genai_types.Content]:
    """Convert Anthropic-format messages to Gemini Content objects."""
    contents = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(genai_types.Content(
            role=role,
            parts=[genai_types.Part(text=msg["content"])],
        ))
    return contents


class GeminiClient:
    """Google Gemini-backed LLM client with tool use support."""

    def __init__(
        self,
        model: str = "gemini-3-flash-preview",
        api_key: str | None = None,
        max_tokens: int = 1024,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.client = genai.Client(
            api_key=api_key or os.environ.get("GEMINI_API_KEY"),
        )

    async def generate(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        config = genai_types.GenerateContentConfig(
            max_output_tokens=self.max_tokens,
        )
        if system:
            config.system_instruction = system
        if tools:
            config.tools = _anthropic_tools_to_gemini(tools)

        contents = _anthropic_messages_to_gemini(messages)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                break
            except genai_errors.ClientError as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    raise QuotaExhaustedError(str(e)) from e
                raise
            except genai_errors.ServerError as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    if attempt < max_retries - 1:
                        await asyncio.sleep(30)
                        continue
                    raise ServiceUnavailableError(str(e)) from e
                raise

        # Parse response
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        if response.text:
            text_parts.append(response.text)

        if response.function_calls:
            for call in response.function_calls:
                tool_calls.append({
                    "id": call.id or call.name,
                    "name": call.name,
                    "input": call.args or {},
                })

        return LLMResponse(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            raw=response,
        )


# ---------------------------------------------------------------------------
# OpenRouter implementation
# ---------------------------------------------------------------------------

def _anthropic_tools_to_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic-format tool definitions to OpenAI function calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            },
        }
        for tool in tools
    ]


class OpenRouterClient:
    """OpenRouter-backed LLM client (OpenAI-compatible API with tool use support)."""

    def __init__(
        self,
        model: str = "qwen/qwen3.6-plus-preview:free",
        api_key: str | None = None,
        max_tokens: int = 1024,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.client = openai.AsyncOpenAI(
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )

    async def generate(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": all_messages,
        }
        if tools:
            kwargs["tools"] = _anthropic_tools_to_openai(tools)
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        text = message.content or ""
        tool_calls: list[dict[str, Any]] = []

        if message.tool_calls:
            import json
            for call in message.tool_calls:
                tool_calls.append({
                    "id": call.id,
                    "name": call.function.name,
                    "input": json.loads(call.function.arguments),
                })

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            raw=response,
        )


# ---------------------------------------------------------------------------
# HuggingFace (local TGI / HF Inference API) implementation
# ---------------------------------------------------------------------------

class HuggingFaceClient:
    """HuggingFace-backed LLM client via AsyncInferenceClient.

    Works with:
    - A local Text Generation Inference (TGI) server (default: http://localhost:8080)
    - The HuggingFace Inference API (set api_key and omit base_url)
    """

    def __init__(
        self,
        model: str = "tgi",
        base_url: str = "http://localhost:8080/v1",
        api_key: str | None = None,
        max_tokens: int = 1024,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.client = AsyncInferenceClient(
            base_url=base_url,
            api_key=api_key or os.environ.get("HF_API_KEY", "local"),
        )

    async def generate(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        import json

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": all_messages,
        }
        if tools:
            kwargs["tools"] = _anthropic_tools_to_openai(tools)
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        text = message.content or ""
        tool_calls: list[dict[str, Any]] = []

        if message.tool_calls:
            for call in message.tool_calls:
                tool_calls.append({
                    "id": call.id,
                    "name": call.function.name,
                    "input": json.loads(call.function.arguments),
                })

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            raw=response,
        )
