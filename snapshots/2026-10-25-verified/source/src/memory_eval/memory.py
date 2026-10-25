from __future__ import annotations

from .types import MemoryEntry, Operation


def apply_operations(store: list[MemoryEntry], ops: list[Operation], session_id: str) -> list[MemoryEntry]:
    """Apply only well-formed operations; invalid references become harmless no-ops."""
    result = list(store)
    by_id = {entry.id: index for index, entry in enumerate(result)}
    next_id = max((int(e.id.removeprefix("mem_")) for e in result if e.id.startswith("mem_") and e.id[4:].isdigit()), default=0) + 1
    for op in ops:
        if op.op == "add" and op.content:
            entry = MemoryEntry(id=f"mem_{next_id}", content=op.content.strip(), source_session=session_id)
            next_id += 1
            by_id[entry.id] = len(result)
            result.append(entry)
        elif op.op == "update" and op.id in by_id and op.content:
            old = result[by_id[op.id]]
            result[by_id[op.id]] = MemoryEntry(id=old.id, content=op.content.strip(), source_session=session_id)
        elif op.op == "delete" and op.id in by_id:
            result.pop(by_id[op.id])
            by_id = {entry.id: index for index, entry in enumerate(result)}
    return result
