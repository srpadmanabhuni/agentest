# r13 version note

Unreleased. Not tagged, not merged, and not published.

T6-001 and T6-008 read constraints from any user turn: caps, exclusions, "do not" instructions and
object pins. Later writes are checked against the constraints still in force. The judge is used only
to extract those constraints; answers are cached, and a deterministic extractor is the fallback when
the judge has no answer. T6-008 requires a constraint to still hold 5 or more turns after it was set.

A conversation with no constraint is `n/a`. The catalogue revision, the 38-test assessable scope,
aggregation, thresholds, and the rule that `n/a` on a labelled defect is a miss are unchanged.

See [Constraint memory](../standards/CONSTRAINT-MEMORY.md).
