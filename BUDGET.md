# Synthetic-evaluation budget plan

Last refreshed: 2026-10-25. Prices are OpenRouter list prices captured from its live model catalog; refresh them before later large runs. The former MiniMax free model ID is no longer listed, so this snapshot uses the paid `minimax/minimax-m3.1-flash` ID.

## Scope and assumptions

- Corpus: 4 synthetic threads = 14 sessions (the Atlas thread has two sessions).
- Targets: local Hy-Memory plus 8 OpenRouter models.
- Costed remote calls: 8 paid models × 14 sessions = 112 calls.
- Planning allowance per memory write: 1,000 input tokens + 1,500 output tokens, matching the configured output cap. This is **not a hard cost ceiling**: long transcripts and accumulated stores can use substantially more than 1,000 input tokens. Use provider usage records for actual spend.

## Stages

| Stage | Scope | Estimated cost |
|---|---|---:|
| Smoke | Atlas thread, two sessions across every target | $0.32 |
| Full synthetic | 14 sessions across every target | $2.27 |
| Automatic scoring | Up to 126 GLM-5.3 judge calls at the same 1K/1K allowance | $0.19 |
| Full synthetic plus judging | All of the above | $2.46 |
| Planning guardrail | 25% contingency above the estimate | $3.07 |

Real-transcript and BEAM runs are not covered by this plan: their input cost depends on actual transcript lengths and should be estimated separately.

## Per-model full-synthetic estimates

| Model | Estimated cost |
|---|---:|
| GLM-5.3 Flash | $0.0126 |
| GLM-5.3 | $0.0305 |
| MiniMax M3.1 Flash | $0.0147 |
| Claude Opus 5.5 | $0.4760 |
| GPT-6 Astra | $1.1900 |
| Gemini 4 Argon | $0.2380 |
| Grok 4.7 | $0.1540 |
| Qwen3.8 Max | $0.1540 |
