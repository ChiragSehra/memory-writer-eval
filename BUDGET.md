# Synthetic-evaluation budget plan

Last refreshed: 2026-10-22. Prices are OpenRouter list prices captured from its live model catalog; refresh them before any large run.

## Scope and assumptions

- Corpus: 3 synthetic threads × 4 sessions = 12 sessions.
- Targets: local Hy-Memory plus 8 OpenRouter models.
- Costed remote calls: 7 paid models × 12 sessions = 84 calls.
- Free remote calls: 1 free model × 12 sessions = 12 calls.
- Conservative per-memory-write allowance: 1,000 input tokens + 1,000 output tokens. The configured output cap is 1,000 tokens; the input allowance leaves room for the prompt, transcript, and accumulated store.

## Stages

| Stage | Scope | Estimated ceiling |
|---|---|---:|
| Smoke | One thread × two sessions across every target | $0.23 |
| Full synthetic | 12 sessions across every target | $1.36 |
| Automatic scoring | 30 GLM-5.3 judge calls | $0.02 |
| Full synthetic plus judging | All of the above | $1.38 |
| Approval guardrail | 25% contingency above the estimate | $1.73 |

The free-model calls are subject to OpenRouter’s free-tier request allowance, not a dollar charge. Real-transcript runs are not covered by this plan: their input cost depends on the actual transcript lengths and should be estimated separately.

## Per-model full-synthetic ceilings

| Model | Estimated ceiling |
|---|---:|
| GLM-5.3 Flash | $0.0024 |
| GLM-5.3 | $0.0177 |
| MiniMax M3.1 Flash (free) | $0.00 |
| Claude Opus 5.5 | $0.2880 |
| GPT-6 Astra | $0.7200 |
| Gemini 4 Argon | $0.1440 |
| Grok 4.7 | $0.0960 |
| Qwen3.8 Max | $0.0960 |
