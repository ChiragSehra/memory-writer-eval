# BEAM 1M memory-only pilot

Source: [official BEAM benchmark](https://github.com/mohammadtavakoli78/BEAM), 1M chat 1 and its 20 probe questions. This is an exploratory rubric score, not a leaderboard-comparable result: the reader saw only the final memory store, and the rubric checker does not reproduce every rule in BEAM's official evaluator.

Writer: `openrouter:glm-5.3`; reader: `openrouter:glm-5.3`; judge: `google/gemini-4-argon`. Writer JSON valid: 10/10; provider-reported writer input tokens: 1,021,674; final memory entries: 107; answered probes: 20/20.

| Ability | Scored | Mean rubric score |
|---|---:|---:|
| abstention | 2/2 | 50.0% |
| contradiction_resolution | 2/2 | 12.5% |
| event_ordering | 2/2 | 35.0% |
| information_extraction | 2/2 | 100.0% |
| instruction_following | 2/2 | 100.0% |
| knowledge_update | 2/2 | 100.0% |
| multi_session_reasoning | 2/2 | 25.0% |
| preference_following | 2/2 | 87.5% |
| summarization | 2/2 | 35.8% |
| temporal_reasoning | 2/2 | 62.5% |
| **All abilities** | 20/20 | 60.8% |
