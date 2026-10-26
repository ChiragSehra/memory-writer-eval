# Invented facts as a share of writes

A write is an applied `add` or `update` operation. Deletes, noops, invalid references, and empty-content operations are excluded. Every applied write is counted even if later changed or deleted. A write with any unsupported detail is labeled unsupported. `Supported but not worth storing` counts facts the judge found grounded in user statements but transient, redundant, or otherwise low-value for long-term memory. These are automated second-judge labels; review ambiguous cases before treating the rates as ground truth.

| Model | Writes | Judge coverage | Unsupported / writes | Supported but not worth storing / writes | Uncertain / writes |
|---|---:|---:|---:|---:|---:|
| local | 26 | 26/26 | 4/26 (15.4%) | 3/26 (11.5%) | 0/26 (0.0%) |
| openrouter:claude-opus-5.5 | 18 | 18/18 | 1/18 (5.6%) | 0/18 (0.0%) | 0/18 (0.0%) |
| openrouter:gemini-4-argon | 21 | 21/21 | 1/21 (4.8%) | 1/21 (4.8%) | 0/21 (0.0%) |
| openrouter:glm-5.3 | 16 | 16/16 | 0/16 (0.0%) | 0/16 (0.0%) | 0/16 (0.0%) |
| openrouter:glm-5.3-flash | 20 | 20/20 | 1/20 (5.0%) | 0/20 (0.0%) | 0/20 (0.0%) |
| openrouter:gpt-6-astra | 19 | 19/19 | 0/19 (0.0%) | 0/19 (0.0%) | 0/19 (0.0%) |
| openrouter:grok-4.7 | 22 | 22/22 | 0/22 (0.0%) | 1/22 (4.5%) | 0/22 (0.0%) |
| openrouter:minimax-m3.1-flash-free | 23 | 23/23 | 1/23 (4.3%) | 1/23 (4.3%) | 0/23 (0.0%) |
| openrouter:qwen3.8-max | 16 | 16/16 | 0/16 (0.0%) | 2/16 (12.5%) | 0/16 (0.0%) |
| **All models** | 181 | 181/181 | 8/181 (4.4%) | 8/181 (4.4%) | 0/181 (0.0%) |
