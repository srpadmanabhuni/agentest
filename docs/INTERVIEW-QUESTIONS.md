# Agent testing interview questions and flashcards

**Study material for testers and developers who test tool-using AI agents: 20 questions with short answers grounded in the checklist, plus all 110 test designs as flashcards.** Use it to prepare for an interview, to run one for your team, or to check your progress on the [learning roadmap](LEARNING-ROADMAP.md).

## Flashcards for the 110 designs

```bash
python scripts/checklist_flashcards.py --out agentest-flashcards.csv            # all 110
python scripts/checklist_flashcards.py --priority P0 --out p0-flashcards.csv    # the 47 P0 designs
```

Front: ID and title. Back: objective, pass signal and fail signal. Tags: class, priority, severity. Import the CSV into Anki (File, Import, comma separated, fields Front, Back, Tags) or any flashcard app that reads CSV.

## Questions

### Foundations

1. **Why is checking the agent's final reply not enough?** The reply can claim work that never happened. The trace records what the agent actually called and what came back, so a test can compare the claim with the evidence (T1-005, T1-018).
2. **What is an agent trace, and what do you extract from it?** A recording of one run as spans: the agent turn, each tool call with its arguments and result. In OpenTelemetry GenAI terms, `gen_ai.tool.name` and `gen_ai.tool.call.arguments`. See [Build your own agent test](BUILD-YOUR-OWN-AGENT-TEST.md).
3. **What should a test say when the trace has no evidence for it?** `n/a`, never `pass`. A silent pass hides missing coverage.
4. **Why prefer deterministic rules over a model judge for these checks?** Same trace, same verdict, every time; the evidence can be shown line by line; no API key or network in CI. A model judge can still help for open-ended quality, as a separate step.
5. **What is a teaching fixture, and why label it?** A deliberately buggy sample agent (here `eager`, `refill_bot_buggy`). It shows what a failure looks like; it says nothing about how often real agents fail.

### Tools and ordering

6. **How do you test that an agent only uses permitted tools?** Compare every recorded tool name with the declared list (MCP `tools.json`), and every URL host with the allowed hosts (T5-001, T5-005).
7. **What is a dependency-ordering bug?** A step that needs a prerequisite runs before it, for example a refill placed before identity is verified (T2-001).
8. **How do you test for a duplicated irreversible action?** Count the irreversible calls for one intent; more than one fails (T2-003).

### State, handover and orchestration

9. **What is state drift?** A value agreed earlier changes later without the user asking: amount 4500 becomes 4550, ticket T-9 becomes T-OTHER (T6-002, T6-003).
10. **Why is a handover note not an approval?** Free text can be written by anyone, including an injected document. Approval must come from an authorised actor as a verifiable, single-use token (T3-001, T3-010).
11. **What extra risk do multi-agent systems add?** Authority and context pass between agents; a sub-agent can act with more authority than the user granted, or lose a constraint at the handoff. Test the actor and the approval on every privileged step.

### Red teaming and privacy

12. **What is indirect prompt injection?** An instruction hidden in content the agent reads (a resume, an email, tool output) rather than typed by the user. Test that no planted value reaches a later write, recipient or reply (T4-001, T4-003, T4-009).
13. **How do you test for personal data leaks?** Look for raw personal data in tool arguments (T5-004), in replies to rephrased asks (T7-014), and secrets repeated on later turns (T6-011).
14. **Why test paraphrases and translations?** A safe behaviour that holds for one wording can break for another. Metamorphic tests compare runs that should behave the same (T7 class, for example T7-002 and T7-014).
15. **Name two limits of pattern-based privacy checks.** They only recognise the formats they know (for example one phone number style), and they can flag look-alike values. Read the false-positive notes and widen the patterns with care.

### Process and CI

16. **How do you gate a release on agent tests?** Run the checks on recorded traces in CI and exit non-zero on any `fail` (`--strict`, JUnit or SARIF output). See [tutorial 4](tutorials/04-ci-cd-github-actions.md).
17. **Where do the traces for CI come from?** Recorded runs of fixed scenarios, exported as OpenTelemetry GenAI spans by your framework or a small exporter, versioned next to the tests.
18. **How do you keep a checker honest?** Labels written before predictions are run and locked with a hash, fresh held-out traces, and a record of every verdict a rule change flips ([labelling](contributing/LABELLING.md), [CI verdict diff](contributing/CI-VERDICT-DIFF.md)).
19. **What does a good bug report for an agent look like?** The trace (redacted), the check ID, the verdict detail, the expected behaviour, and one command that reproduces it.
20. **How would you start testing an agent you have never seen?** Get one trace, run the P0 checks, read every `fail` and `n/a`, then add scenario traces for the risks that matter most for that agent ([challenge](CHALLENGE.md) and the [roadmap](LEARNING-ROADMAP.md)).

Found a better answer or a missing question? Enhance and contribute: open a pull request against this page.
