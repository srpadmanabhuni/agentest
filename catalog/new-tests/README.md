# New tests catalogue fragments

One JSONL file per batch (`b1.jsonl` .. `b5.jsonl`). `agentest.standards.catalog.new_tests()` merges every `*.jsonl`
here and sorts by ID, so batches never edit the same file. Each line is one row:

| Field | Meaning |
|:--|:--|
| `id` | `NT-001` upwards. The published test count does not grow when a later fragment adds an ID. |
| `class_id` | `NT` |
| `title` | Short name of the check |
| `article_test` | Article test it closes, e.g. `A002` |
| `article_title` | Article test title |
| `objective` | What the check is for |
| `acceptance_criteria` | Pass, fail and n/a rules |
| `trace_attributes` | Span attributes the check reads (list) |
| `batch` | `b1` .. `b5` |

New tests are opt-in: `agentest list --new-tests`, `agentest std run --ids NT` (all) or `--ids NT-001,NT-002`.
