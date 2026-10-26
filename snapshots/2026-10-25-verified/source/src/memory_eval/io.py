from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_session(path: Path) -> dict[str, Any]:
    if path.suffix == ".json":
        session = json.loads(path.read_text())
        if "messages" in session:
            messages = session["messages"]
            if not isinstance(messages, list) or not messages:
                raise ValueError(f"messages must be a nonempty list in {path}")
            seen = set()
            lines = []
            for message in messages:
                if not isinstance(message, dict) or not isinstance(message.get("message_id"), str) or not message["message_id"] or message["message_id"] in seen:
                    raise ValueError(f"messages need unique nonempty message_id values in {path}")
                if message.get("role") not in {"user", "assistant", "tool", "system"} or not isinstance(message.get("content"), str):
                    raise ValueError(f"invalid message role or content in {path}")
                seen.add(message["message_id"])
                lines.append(f"[{message['message_id']}] {message['role']}: {message['content']}")
            session["transcript"] = "\n".join(lines)
        return session
    return {"session_id": path.stem, "transcript": path.read_text()}


def load_threads(directory: str | Path) -> dict[str, list[dict[str, Any]]]:
    threads: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(Path(directory).glob("*")):
        if path.suffix not in {".json", ".md", ".markdown"}:
            continue
        if path.stem.endswith("__ground_truth"):
            continue
        session = read_session(path)
        thread_id = session.get("thread_id", path.stem.split("__")[0])
        session["session_id"] = session.get("session_id", path.stem)
        threads.setdefault(thread_id, []).append(session)
    for sessions in threads.values():
        sessions.sort(key=lambda item: (item.get("sequence", 0), item["session_id"]))
        message_ids = set()
        for session in sessions:
            for message in session.get("messages", []):
                if message["message_id"] in message_ids:
                    raise ValueError(f"Duplicate message_id across sessions: {message['message_id']}")
                message_ids.add(message["message_id"])
    return threads


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
