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
```

The generated report is written to `runs/<timestamp>/report.md`. Run artifacts are deliberately ignored by Git.

## Configuration

[`config.yaml`](config.yaml) contains the local endpoint, enabled OpenRouter targets, JSON-mode settings, runtime limits, and price assumptions. It contains no hosted credentials: the OpenRouter key is read only from `OPENROUTER_API_KEY`.

Update `pricing_usd_per_million_tokens` from the provider's current catalog before using the cost output for a large run. See [BUDGET.md](BUDGET.md) for the current staged synthetic-run assumptions.

## Real transcripts and review

Place one JSON or Markdown session per file in `data/transcripts/`. JSON records require `thread_id`, `session_id`, `sequence`, and `transcript`; filenames such as `project-a__session-01.json` also work.

Real transcripts are ignored by Git to prevent accidental publication. Review the data yourself before sharing it anywhere.

Create a blinded human-review sheet with:

```bash
uv run memory-eval export-blind runs/<timestamp>
```

After scoring, restore model identities with:

```bash
uv run memory-eval merge-scores \
  scoring/blind_sheet.csv \
  scoring/blind_sheet_key.csv \
  scoring/merged_scores.csv
```

Scoring exports, including the identity key, are ignored by Git.

## Repository layout

```text
src/memory_eval/    CLI, model writer, memory operations, runner, and scoring
prompts/            Memory-writer instruction prompt
data/synthetic/     Versioned synthetic sessions and ground truth
data/transcripts/   Local-only real transcripts
scoring/            Local-only human-review exports
runs/               Local-only generated reports and raw model outputs
```

## Safety and evaluation boundaries

- Never place API keys in `config.yaml`, transcripts, run artifacts, or commits.
- Reasoning-stream deltas are ignored; only visible final JSON is parsed as memory operations.
- Invalid output is not applied to a memory store.
- Treat automatic semantic scores as evidence to investigate, not a substitute for blinded review or downstream task evaluation.
