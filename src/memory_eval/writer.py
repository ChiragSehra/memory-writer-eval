from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from .types import CallResult, Operation


class MemoryWriter:
    """One OpenAI-SDK client shape for LM Studio and Z.AI."""

    def __init__(self, name: str, settings: dict[str, Any], runtime: dict[str, Any]) -> None:
        self.name = name
        self.settings = settings
        self.runtime = runtime
        key_env = settings.get("api_key_env")
        api_key = os.environ.get(key_env) if key_env else settings.get("api_key", "lm-studio")
        if not api_key:
            raise RuntimeError(f"{key_env} is required for {name} (it is never written to disk).")
        self.client = OpenAI(
            base_url=settings["base_url"],
            api_key=api_key,
            timeout=runtime.get("request_timeout_s", 45),
            max_retries=0,
        )
        self.model = settings["model"]

    def list_models(self) -> list[str]:
        return [model.id for model in self.client.models.list().data]

    def _extra_body(self) -> dict[str, Any]:
        if self.settings.get("provider") != "zai":
            return {}
        thinking = self.settings.get("thinking", False)
        model = str(self.model).lower()
        if thinking:
            return {"thinking": {"type": "enabled"}}
        # GLM-5.3 family cannot disable thinking. Low separates reasoning into
        # reasoning_content; streaming code below discards it completely.
        if model.startswith("glm-5.3"):
            return {"thinking": {"type": "enabled"}, "reasoning_effort": "low"}
        return {"thinking": {"type": "disabled"}}

    def _stream(self, messages: list[dict[str, str]], json_mode: bool, response_format: dict[str, Any] | None = None) -> CallResult:
        started = time.perf_counter()
        request: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": self.runtime.get("temperature", 0),
            "max_tokens": self.runtime.get("max_output_tokens", 1000),
            "extra_body": self._extra_body(),
        }
        if json_mode and self.settings.get("supports_json_mode", True):
            request["response_format"] = response_format or self._response_format()
        stream = self.client.chat.completions.create(**request)
        first_token: float | None = None
        chunks: list[str] = []
        usage = None
        # Intentionally ignore delta.reasoning_content: only visible content may be memory JSON.
        for chunk in stream:
            if getattr(chunk, "usage", None):
                usage = chunk.usage
            choices = getattr(chunk, "choices", [])
            if not choices:
                continue
            delta = choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                if first_token is None:
                    first_token = time.perf_counter()
                chunks.append(content)
        ended = time.perf_counter()
        return CallResult(
            raw_content="".join(chunks),
            reasoning_content="",  # never retain or parse hidden thinking output
            latency_ttft_s=(first_token - started) if first_token else None,
            latency_total_s=ended - started,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            retries=0,
            json_valid=False,
        )

    def _response_format(self) -> dict[str, Any]:
        if self.settings.get("json_mode", "json_object") != "json_schema":
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "memory_operations",
                "schema": {
                    "type": "object",
                    "properties": {
                        "ops": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "op": {"type": "string", "enum": ["add", "update", "delete", "noop"]},
                                    "id": {"type": ["string", "null"]},
                                    "content": {"type": ["string", "null"]},
                                    "reason": {"type": "string"},
                                },
                                "required": ["op", "id", "content", "reason"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["ops"],
                    "additionalProperties": False,
                },
            },
        }

    @staticmethod
    def _parse_operations(text: str) -> list[Operation]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        value = json.loads(cleaned)
        if not isinstance(value, dict) or not isinstance(value.get("ops"), list):
            raise ValueError("Expected an object with an ops array")
        operations: list[Operation] = []
        for item in value["ops"]:
            if not isinstance(item, dict) or item.get("op") not in {"add", "update", "delete", "noop"}:
                raise ValueError("Invalid operation")
            operations.append(Operation(op=item["op"], id=item.get("id"), content=item.get("content"), reason=str(item.get("reason", ""))))
        return operations

    def write(self, prompt: str, memory_json: str, transcript: str) -> tuple[list[Operation], CallResult]:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"CURRENT MEMORY STORE:\n{memory_json}\n\nNEW SESSION TRANSCRIPT:\n{transcript}"},
        ]
        last = None
        for attempt in range(2):
            try:
                result = self._stream(messages, json_mode=True)
            except Exception as exc:
                return [], CallResult(
                    raw_content="",
                    reasoning_content="",
                    latency_ttft_s=None,
                    latency_total_s=0,
                    input_tokens=None,
                    output_tokens=None,
                    retries=attempt,
                    json_valid=False,
                    error=f"{type(exc).__name__}: {exc}",
                )
            result.retries = attempt
            try:
                ops = self._parse_operations(result.raw_content)
                result.json_valid = True
                return ops, result
            except (json.JSONDecodeError, ValueError) as exc:
                last = result
                messages.append({"role": "user", "content": "Your last response was invalid. Return only a valid JSON object matching the required ops schema."})
                last.error = str(exc)
        assert last is not None
        return [], last

    def tiny_test(self) -> CallResult:
        return self._stream([{"role": "user", "content": "Reply with exactly: ok"}], json_mode=False)


def prompt_text(path: str | Path = "prompts/memory_writer.md") -> str:
    return Path(path).read_text()
