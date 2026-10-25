# Memory Writer Eval

A small evaluation harness for LLMs that write long-term agent memory. It compares a local LM Studio model with OpenRouter models using the same prompt, JSON operation schema, synthetic sessions, and per-model memory stores.

The harness evaluates the write path, not retrieval: given a memory store and one new session transcript, a model emits `add`, `update`, `delete`, or `noop` operations. Only durable facts explicitly stated by the user should be retained.

## What it measures

- Structured-output reliability, including invalid JSON and retries.
- Latency, token throughput, and configured token cost.
- Synthetic memory recall, unsupported entries, duplicates, and stale facts.
- Blinded human-review exports for qualitative scoring.

It does not claim that synthetic judge scores alone select a production model. In particular, a model judging its own outputs is a regression signal, not independent evaluation.

## Requirements

- Python 3.10 or newer.
- [uv](https://docs.astral.sh/uv/).
- An OpenAI-compatible LM Studio server for the local target (optional if you remove it from `config.yaml`).
- `OPENROUTER_API_KEY` for configured hosted targets.

## Quick start

```bash
uv sync
export OPENROUTER_API_KEY='...'

# Confirm local and hosted endpoints before spending on a run.
uv run memory-eval preflight

# Rebuild the synthetic corpus, if needed.
uv run memory-eval generate-synthetic

# Run a small smoke test first.
uv run memory-eval run --input data/synthetic --threads 1 --sessions 2

# Run the complete synthetic panel.
uv run memory-eval run --input data/synthetic
uv run memory-eval score-synthetic runs/<timestamp>

# Repair only failed judge verdicts while retaining successful ones.
uv run memory-eval score-synthetic runs/<timestamp> --retry-errors
```

The generated report is written to `runs/<timestamp>/report.md`. Run artifacts are deliberately ignored by Git.

## Configuration

[`config.yaml`](config.yaml) contains the local endpoint, enabled OpenRouter targets, JSON-mode settings, runtime limits, and price assumptions. It contains no hosted credentials: the OpenRouter key is read only from `OPENROUTER_API_KEY`.

Update `pricing_usd_per_million_tokens` from the provider's current catalog before using the cost output for a large run. See [BUDGET.md](BUDGET.md) for the current staged synthetic-run assumptions.

## Real transcripts and review

Place one JSON or Markdown session per file in `data/transcripts/`. JSON records require `thread_id`, `session_id`, and `sequence`; supply either a `transcript` string or a `messages` array. Message-level provenance requires the structured form:

```json
{
  "thread_id": "project-a",
  "session_id": "session-01",
  "sequence": 1,
  "messages": [
    {"message_id": "project-a-001", "role": "user", "content": "Our weekly review is Friday."},
    {"message_id": "project-a-002", "role": "assistant", "content": "Understood."}
  ]
}
```

Message IDs must be unique within a thread across its sessions. Supported
roles are `user`, `assistant`, `tool`, and `system`. The runner formats these
messages into the writer's transcript while retaining IDs in the source JSON.

Real transcripts are ignored by Git to prevent accidental publication. Review the data yourself before sharing it anywhere.

The 2026-10-26 real-data pilot uses three English, non-toxic, non-redacted multi-turn conversations from the public [WildChat-1M dataset](https://huggingface.co/datasets/allenai/WildChat-1M). `scoring/real_source_manifest.json` records its revision, source row numbers, conversation hashes, and text digests. The imported sessions retain only user/assistant text and role-qualified turn IDs; IP-derived fields and request headers are discarded. This is a hand-selected convenience sample, not a representative estimate of real-world performance. Public-data redaction is not a guarantee that every sensitive detail was removed, so keep the imported sessions and scored quotes local.

Create a blinded human-review sheet with:

```bash
uv run memory-eval export-blind runs/<timestamp> --input data/synthetic
```

After scoring, restore model identities with:

```bash
uv run memory-eval merge-scores \
  scoring/blind_sheet.csv \
  scoring/blind_sheet_key.csv \
  scoring/merged_scores.csv
```

Scoring exports, including the identity key, are ignored by Git.

For an independent automated review of the blinded entries, run a configured
OpenRouter model other than `judge.name` against the export:

```bash
uv run memory-eval score-blind scoring/blind_sheet.csv --judge gemini-4-argon
```

The second judge sees each entry and its full transcript history, but never the
model identity key. Its verdicts go to `scoring/second_judge_scores.csv` and
can be resumed after interruption. Review the evidence quotes and uncertain
verdicts manually; this model score does not replace human scoring. Because
Gemini is also a writer target, its own writer rows are self-judged even though
it is independent of the primary GLM judge.

To count unsupported facts over actual writes, including entries that were
subsequently updated or removed:

```bash
uv run memory-eval export-writes runs/<timestamp> --input data/synthetic
uv run memory-eval score-blind scoring/write_sheet.csv \
  --judge gemini-4-argon --output scoring/write_judge_scores.csv
uv run memory-eval report-writes \
  scoring/write_sheet.csv scoring/write_sheet_key.csv \
  scoring/write_judge_scores.csv
```

The report denominator is every applied `add` or `update` operation. Its
"unsupported" label means the write is not wholly grounded in explicit user
statements; it does not establish that the detail is false in the world.

To blind-score complete stores at every synthetic checkpoint, including an
empty store after an invalid writer response:

```bash
uv run memory-eval export-checkpoints runs/<timestamp> --input data/synthetic
uv run memory-eval score-checkpoints scoring/checkpoint_sheet.csv \
  --judge gemini-4-argon
uv run memory-eval report-checkpoints \
  scoring/checkpoint_sheet.csv scoring/checkpoint_sheet_key.csv \
  scoring/checkpoint_judge_scores.csv
```

The checkpoint sheet also has blank columns for human review. Model identities
and writer validity are kept in the separate key file.

Break unsupported writes down by primary cause:

```bash
uv run memory-eval classify-writes scoring/write_sheet.csv \
  scoring/write_judge_scores.csv --judge gemini-4-argon
uv run memory-eval report-write-types scoring/write_sheet_key.csv \
  scoring/write_failure_types.csv
```

The classification uses one primary cause per unsupported write and retains
the source evidence quote for audit. A supported but low-value write is counted
separately in the write-level verdict, not as an invented fact.

For a structured real-transcript run, export and score write provenance:

```bash
uv run memory-eval run --input data/transcripts
uv run memory-eval export-writes runs/<timestamp> --input data/transcripts
uv run memory-eval export-traces scoring/write_sheet.csv \
  scoring/write_sheet_key.csv --input data/transcripts
uv run memory-eval score-traces scoring/trace_sheet.csv \
  --judge gemini-4-argon
uv run memory-eval report-traces scoring/trace_sheet.csv \
  scoring/write_sheet_key.csv \
  scoring/trace_scores.csv
```

Trace scoring sends the structured messages to the configured OpenRouter judge.
Each accepted quote is verified against its cited user message ID. The trace
CSV and source sessions remain local and ignored by Git.

For a 1M-scale BEAM write-path and memory-only reader pilot, download one
official `chat.json` and its `probing_questions.json` from the
[BEAM repository](https://github.com/mohammadtavakoli78/BEAM), then run:

```bash
uv run memory-eval import-beam data/beam/beam-1m-chat-1.json \
  --chat-id beam-1m-chat-1 --output data/beam_sessions
uv run memory-eval run --input data/beam_sessions \
  --models openrouter:glm-5.3 --max-output-tokens 4000 \
  --reasoning-effort low --request-timeout-s 180
uv run memory-eval answer-beam runs/<timestamp> \
  data/beam/beam-1m-chat-1-questions.json \
  --writer openrouter:glm-5.3 --reader openrouter:glm-5.3 \
  --expected-sessions 10
uv run memory-eval score-beam-pilot scoring/beam_answers.json \
  data/beam/beam-1m-chat-1-questions.json --judge gemini-4-argon
```

The pilot measures provider-reported writer input tokens, writer JSON validity,
final store size, and performance on the 20 official probes. The lightweight
rubric checker is exploratory and does not reproduce BEAM's official scoring
pipeline or provide a comparable leaderboard number. The local
`scoring/beam_pilot_audit.md` checks source and question hashes, probe joins,
and score arithmetic. The original saved rubric records predate input hashes;
future score runs bind each verdict to its exact question, rubric, and answer.

## Dated synthetic snapshot

The frozen 2026-10-25 panel is in `snapshots/2026-10-25-verified/`. It contains
the synthetic inputs and code used at freeze time, all checkpoint results,
blinded sheets and identity keys, judge scores, and a manifest of hashes. Check
the archive independently of later development with:

```bash
uv run memory-eval verify-snapshot snapshots/2026-10-25-verified
uv run python -m unittest tests.test_frozen_snapshot_evidence -q
```

Add `--check-workspace` only when you also want the **current** source tree to
match that historical version; normal subsequent edits make that stricter
comparison fail. The second command also checks the row-level joins, write
replay, score hashes, and reported coverage; file hashes alone do not prove
those semantic relationships. The readout is in `scoring/snapshot_readout.md`.
The targeted label audit in `scoring/synthetic_label_audit.md` corroborates the unsupported
write flags but finds several "supported yet low-value" flags debatable.

## Repository layout

```text
src/memory_eval/    CLI, model writer, memory operations, runner, and scoring
prompts/            Memory-writer instruction prompt
data/synthetic/     Versioned synthetic sessions and ground truth
data/transcripts/   Local-only real transcripts
scoring/            Aggregate reports plus ignored row-level CSV exports
snapshots/          Frozen, hash-checked synthetic run and source bundle
runs/               Local-only generated reports and raw model outputs
```

## Safety and evaluation boundaries

- Never place API keys in `config.yaml`, transcripts, run artifacts, or commits.
- Reasoning-stream deltas are ignored; only visible final JSON is parsed as memory operations.
- Invalid output is not applied to a memory store.
- Treat automatic semantic scores as evidence to investigate, not a substitute for blinded review or downstream task evaluation.
