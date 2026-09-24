# DS1 Repeated-Group Audit

Scope: final `ds1_700.jsonl` (post Decision-2 KEEP; no dedupe applied).

## The 7 requested statistics

| # | statistic | value |
|---|---|---|
| 1 | unique (model, prompt) groups | 60 |
| 2 | records belonging to repeated groups | 122 |
| 3 | group-size distribution (size: # groups) | {"2": 58, "3": 2} |
| 4 | largest group size | 3 |
| 5 | groups with 2 responses | 58 |
| 6 | groups with 3 responses | 2 |
| 7 | groups with 4+ responses | 0 |
| 8 | any single (model, prompt) dominates the 700? | no (largest group = 3 / 700, 0.43%) |
