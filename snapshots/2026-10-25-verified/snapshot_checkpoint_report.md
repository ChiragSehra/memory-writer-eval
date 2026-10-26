# Blind checkpoint scoring

One blinded row represents a complete model memory store after one session, including empty stores and invalid writer responses. The second judge sees the full history and checkpoint ground truth. Counts below are automated judgments and require human review before publication.

| Model | Writer valid | Judge coverage | Expected matched | Unsupported entries | Duplicates | Stale entries |
|---|---:|---:|---:|---:|---:|---:|
| local | 14/14 | 14/14 | 58/60 | 14 | 5 | 3 |
| openrouter:claude-opus-5.5 | 14/14 | 14/14 | 60/60 | 2 | 0 | 0 |
| openrouter:gemini-4-argon | 14/14 | 14/14 | 60/60 | 0 | 0 | 0 |
| openrouter:glm-5.3 | 14/14 | 14/14 | 60/60 | 0 | 0 | 0 |
| openrouter:glm-5.3-flash | 14/14 | 14/14 | 60/60 | 4 | 0 | 1 |
| openrouter:gpt-6-astra | 14/14 | 14/14 | 60/60 | 0 | 0 | 0 |
| openrouter:grok-4.7 | 14/14 | 14/14 | 60/60 | 0 | 0 | 0 |
| openrouter:minimax-m3.1-flash | 14/14 | 14/14 | 60/60 | 9 | 2 | 0 |
| openrouter:qwen3.8-max | 12/14 | 14/14 | 57/60 | 0 | 0 | 6 |
