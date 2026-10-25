# Targeted audit of the 2026-10-25 synthetic write labels

This is an agent analyst review of the blinded Gemini judgments, not independent human adjudication. It compares each flagged entry with the user, assistant, and tool text in the synthetic history. The source CSVs are `snapshot_write_sheet.csv`, `snapshot_write_sheet_key.csv`, and `snapshot_write_scores.csv` (copied into the dated snapshot). Row IDs refer to that frozen sheet.

## Unsupported writes: 13/13 corroborated under the stated rule

The rubric requires **explicit user support** for every detail in an entry; a potentially true tool result is not enough. Eleven entries import at least one detail only present in tool output: rows 28, 29, 54, 108, 111, 137, 172, 179, 193, 221, and 223. For example, the user confirmed the p95 forecast rule, but did not confirm the tool's `2026-W31` validation result (54, 172). The Q4 rollout scope was user-stated, but the `CHG-4821` ticket ID was tool-only (108, 111, 223).

Rows 23 and 236 misdate a change. In the session dated 2026-10-20, the user said the weekly review moves to Wednesday **starting next week**, not the week of 2026-10-20. Both entries assert the earlier week. Under this rubric they are unsupported, even though their other details are grounded.

This corroborates the 13/240 automated count for this synthetic panel, **not** a claim that all 13 facts are false in the world. It also does not establish a general population rate.

## Supported but marked not worth storing: 9/9 reviewed, 7 contestable

Rows 4 and 145 contain clearly transient personal details (next-day travel; spilled coffee and a ten-minute break). Row 145 also includes a durable instruction mixed into the same write.

Rows 38, 48, 155, and 196 say forecast aggregation is undecided and not to assume a method. Those are temporary, but they may be useful negative constraints until a decision replaces them; marking them simply “useless” is debatable. Row 71 likewise records an undecided PagerDuty plan, which could prevent a false decision from being inferred. Row 146 mixes two useful domain facts with a deduplication instruction and should probably be split, not simply discarded. Row 162 records a user-stated deduplication preference that may belong in writer policy rather than project memory.

Accordingly, **9/240 is the second judge's low-value flag count, not an adjudicated useless-write rate**. A public report should either preserve that attribution or omit the headline number pending human review. This audit did not rescore the other 218 writes or every checkpoint.
