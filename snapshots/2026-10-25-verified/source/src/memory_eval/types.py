from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class MemoryEntry:
    id: str
    content: str
    source_session: str


@dataclass
class Operation:
    op: Literal["add", "update", "delete", "noop"]
    id: str | None = None
    content: str | None = None
    reason: str = ""


@dataclass
class CallResult:
    raw_content: str
    reasoning_content: str
    latency_ttft_s: float | None
    latency_total_s: float
    input_tokens: int | None
    output_tokens: int | None
    retries: int
    json_valid: bool
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SessionResult:
    model: str
    thread_id: str
    session_id: str
    memory_before: list[dict[str, str]]
    memory_after: list[dict[str, str]]
    operations: list[dict[str, Any]] = field(default_factory=list)
    call: dict[str, Any] = field(default_factory=dict)
