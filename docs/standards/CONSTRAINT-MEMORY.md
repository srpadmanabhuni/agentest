# Constraint memory (T6-001, T6-008)

T6-001 and T6-008 check that a constraint the user stated is still respected by later writes.
The check lives in `src/agentest/standards/detectors/constraint_memory.py` and is hooked from the
rule registry. It reads the same signals as the other universal rules: OTel GenAI spans
(`gen_ai.conversation.id`, `gen_ai.input.messages`, `gen_ai.tool.call.arguments`) and MCP
`readOnlyHint` (a read is not a write). It does not name an agent, a tool or a scenario.

## What is extracted

From any user turn, not only the first:

- **Caps.** A numeric upper bound ("at most 40", "अधिकतम 40"). Later amount fields
  (`amount`, `price`, `total`, `cost`, `budget`, `value`) must stay at or under the strictest cap.
- **Exclusions and "do not" instructions.** An id, email or short phrase the user said not to touch.
  A later write whose arguments contain that object fails.
- **Object pins.** "Use only QX-11" (or "केवल QX-11"). A later write whose argument value is a
  different id fails.

A later user turn can revoke a constraint by naming the object without forbidding it, by lifting a
cap, or by stating a new cap or a new pin. Writes after the revocation are checked against what remains.

## Judge, cache, fallback

The judge is asked only to extract constraints (guide `turn-constraints`). The request payload is
unchanged, so an existing replay cache still hits. The guide version stays 1 because the answer
schema is unchanged. Extractions are cached for the process, per judge.

When the judge has no answer, the deterministic extractor above is the whole extraction. A forbid or
cap cue that the extractor cannot structure, with no judge answer, leaves the check `not-assessed`.
A conversation with no constraint is `n/a`.

The pass or fail decision is never a judge opinion. It is a comparison of later write arguments with
the extracted constraint.

## T6-008

T6-008 applies only to a conversation of 6 or more turns. A constraint fails it when a write **5 or
more turns after** the turn that set it still breaks it. An earlier slip that is not repeated at that
distance does not fail T6-008 (it can still fail T6-001). A constraint that never reaches 5 turns
later is `n/a` for T6-008.

## Revocation and absence

- A constraint the user revokes, with later writes that obey what is still in force, passes.
- A conversation that states no constraint is `n/a` for both checks.
