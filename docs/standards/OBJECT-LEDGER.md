# Object-effect ledger

T1-006, T1-011 and T2-003 share one check. Inside a single run it is unchanged: a non-idempotent state-changing tool
(MCP `idempotentHint` false) still runs at most once for the same arguments, and two ledger rows for the same effect
on the same object in that run still fail.

The r13 addition compares **effects across every turn and every run of one conversation** (`gen_ai.conversation.id`).
A later turn that applies the same effect to the same object fails, even when each turn called the tool only once.

## What counts as an effect

An effect is one of:

- a ledger entry (`agentest.state_change` with kind `executed` or `unapproved`);
- a path in the diff between `agentest.initial_state` and `agentest.final_state` that a write in that run touched.

A tool call with neither a ledger entry nor a state diff is not an effect. Repeating the call across turns does not fail.

## Object identity

The ledger keys on the object, not on the call:

- id-like fields in the arguments and in the result (`id`, `*_id`, `object`, `reference`, `ref`), skipping free-text
  fields and idempotency keys (`attempt`, `idempotency`, `nonce`, and the same family);
- declared governance objects: `in_scope` segments of `agentest.task.spec`, an `objects` list on the governance
  extension when a card publishes one, and an approval span's object or target when it is an identifier.

A record id that appears only on the result, and was not declared, is the effect instance. A second turn that returns
that same record, with no new ledger row, is the same effect.

## What is not a second effect

- an approval record (`approved` / `granted` is a boolean and the call does not mint a new record id);
- a tool with MCP `idempotentHint` true;
- a retry whose earlier call's result is an error (the failed attempt is not an effect);
- a record the tool marks as a no-op (`changed` false, `already_processed`, equal before/after state).

## Where it lives

`src/agentest/standards/detectors/object_ledger.py` wraps the three rule ids. The within-run function stays in
`rules.py`. A fail that the within-run rule already reports is returned as it was.

## Version note

Unreleased r13 behaviour on the `r12-core47` line. This page is not a release note for a tagged version: the package
version is unchanged, and nothing here is merged, tagged, or published.
