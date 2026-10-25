# Blind checkpoint scoring

One blinded row represents a complete model memory store after one session, including empty stores and invalid writer responses. The second judge sees the full history and checkpoint ground truth. Counts below are automated judgments and require human review before publication.

| Model | Writer valid | Judge coverage | Expected matched | Unsupported entries | Duplicates | Stale entries |
|---|---:|---:|---:|---:|---:|---:|
| local | 12/12 | 12/12 | 51/52 | 12 | 6 | 5 |
| openrouter:claude-opus-5.5 | 12/12 | 12/12 | 52/52 | 1 | 0 | 0 |
| openrouter:gemini-4-argon | 12/12 | 12/12 | 52/52 | 0 | 0 | 0 |
| openrouter:glm-5.3 | 12/12 | 12/12 | 50/52 | 0 | 0 | 2 |
| openrouter:glm-5.3-flash | 12/12 | 12/12 | 47/52 | 4 | 0 | 0 |
| openrouter:gpt-6-astra | 12/12 | 12/12 | 52/52 | 0 | 0 | 0 |
| openrouter:grok-4.7 | 12/12 | 12/12 | 52/52 | 0 | 2 | 0 |
| openrouter:minimax-m3.1-flash-free | 12/12 | 12/12 | 52/52 | 0 | 0 | 0 |
| openrouter:qwen3.8-max | 10/12 | 12/12 | 33/52 | 0 | 0 | 0 |
