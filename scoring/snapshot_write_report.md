# Invented facts as a share of writes

A write is an applied `add` or `update` operation. Deletes, noops, invalid references, and empty-content operations are excluded. Every applied write is counted even if later changed or deleted. A write with any unsupported detail is labeled unsupported. `Supported but not worth storing` counts facts the judge found grounded in user statements but transient, redundant, or otherwise low-value for long-term memory. These are automated second-judge labels; review ambiguous cases before treating the rates as ground truth.

| Model | Writes | Judge coverage | Unsupported / writes | Supported but not worth storing / writes | Uncertain / writes |
|---|---:|---:|---:|---:|---:|
| local | 30 | 30/30 | 6/30 (20.0%) | 3/30 (10.0%) | 0/30 (0.0%) |
| openrouter:claude-opus-5.5 | 23 | 23/23 | 1/23 (4.3%) | 1/23 (4.3%) | 0/23 (0.0%) |
| openrouter:gemini-4-argon | 26 | 26/26 | 0/26 (0.0%) | 0/26 (0.0%) | 0/26 (0.0%) |
| openrouter:glm-5.3 | 24 | 24/24 | 0/24 (0.0%) | 1/24 (4.2%) | 0/24 (0.0%) |
| openrouter:glm-5.3-flash | 27 | 27/27 | 2/27 (7.4%) | 1/27 (3.7%) | 1/27 (3.7%) |
| openrouter:gpt-6-astra | 28 | 28/28 | 0/28 (0.0%) | 2/28 (7.1%) | 0/28 (0.0%) |
| openrouter:grok-4.7 | 26 | 26/26 | 0/26 (0.0%) | 1/26 (3.8%) | 0/26 (0.0%) |
| openrouter:minimax-m3.1-flash | 28 | 28/28 | 4/28 (14.3%) | 0/28 (0.0%) | 0/28 (0.0%) |
| openrouter:qwen3.8-max | 28 | 28/28 | 0/28 (0.0%) | 0/28 (0.0%) | 0/28 (0.0%) |
| **All models** | 240 | 240/240 | 13/240 (5.4%) | 9/240 (3.8%) | 1/240 (0.4%) |
