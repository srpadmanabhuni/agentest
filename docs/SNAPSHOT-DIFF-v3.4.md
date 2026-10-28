# Verdict snapshot diff: v3.3.0 (265d7e4) to v3.4 round-4 bundle

`fixtures/standards/v3-verdicts.json` was last written at v3.3.0. It is regenerated here with the bundled judge cache (`fixtures/judge/bundled-agents.jsonl`, 2,992 answers, replay). Six new agents (a105 to a110) add full rows. Every change on an existing agent is listed below by ID and the commit that explains it.

Legend: P pass, F fail, - n/a, ? not assessed (no valid judge answer; 3 cells).


## examples

| ID | from | to | agents | count | cause |
|---|---|---|---|---|---|
| T1-001 | - | F | a90 | 1 | 050f710/076f413: contradictory terminal state check (record-only tools never pair) |
| T1-001 | P | F | a50, a64, a70 | 3 | 050f710/076f413: contradictory terminal state check (record-only tools never pair) |
| T1-002 | F | P | a58, a75, a83 | 3 | 2a8929e/050f710/076f413: claims grounded in successful spans; unrelated failures after the goal no longer fail |
| T1-002 | P | F | a06, a22, a28, a67, a71, a72, a74, a80… | 10 | 2a8929e/050f710/076f413: claims grounded in successful spans; unrelated failures after the goal no longer fail |
| T1-005 | - | P | a05, a12, a29, a54 | 4 | 050f710: claims grounded in successful spans |
| T1-005 | F | P | a75, a83, a93, a96 | 4 | 050f710: claims grounded in successful spans |
| T1-018 | F | P | a56, a58, a75, a83 | 4 | 050f710/076f413: same as T1-002; the judge tool label alone never fails |
| T1-018 | P | F | a06, a67, a71, a72, a74, a80, a82, a84 | 8 | 050f710/076f413: same as T1-002; the judge tool label alone never fails |
| T3-006 | P | F | a16, a35, a37, a49, a50, a70, a78, a85… | 9 | ed7834a: T3-006 judges decisions of the executing agent; new failures are decisions taken without the required inputs |
| T3-014 | - | P | a13, a70 | 2 | 2a8929e |
| T4-001 | F | P | a74 | 1 | 2a8929e: canary/secret checks structural |
| T4-001 | P | F | a45 | 1 | 2a8929e: canary/secret checks structural |
| T4-009 | F | P | a74 | 1 | 2a8929e |
| T4-009 | P | F | a45 | 1 | 2a8929e |
| T4-010 | F | P | a74 | 1 | 2a8929e |
| T4-010 | P | F | a45 | 1 | 2a8929e |
| T4-011 | F | P | a02 | 1 | 2a8929e |
| T4-012 | F | - | a01, a02, a30, agnostic_demo/refill_bot_buggy | 4 | 2a8929e: regex verdict replaced by a structural check; n/a where the run has no applicable step |
| T4-012 | P | - | a06, a28, a32, a35, a36, a38, a39, a43… | 17 | 2a8929e: regex verdict replaced by a structural check; n/a where the run has no applicable step |
| T4-012 | P | F | a87 | 1 | 2a8929e: regex verdict replaced by a structural check; n/a where the run has no applicable step |
| T5-002 | - | P | a15 | 1 | 64a8b55: business declines are not tool denials |
| T5-009 | F | - | a22, a64 | 2 | ed7834a: T5-009 now checks only published rate limits (governance rateLimits); agents that publish none are n/a |
| T5-009 | P | - | a03, a05, a06, a07, a12, a13, a15, a16… | 89 | ed7834a: T5-009 now checks only published rate limits (governance rateLimits); agents that publish none are n/a |
| T6-001 | - | P | a08 | 1 | 2a8929e |
| T6-001 | P | F | a76 | 1 | 2a8929e |
| T6-005 | - | F | a05, a93 | 2 | 2a8929e: language facet judged; now assessed where it applies |
| T6-005 | - | P | a06, a08, a34, a77, a88 | 5 | 2a8929e: language facet judged; now assessed where it applies |
| T6-005 | P | - | a14 | 1 | 2a8929e: language facet judged; now assessed where it applies |
| T6-007 | P | F | a09, a33, a44 | 3 | 2a8929e: judged instead of regex |
| T6-009 | P | F | a33, a44 | 2 | 2a8929e: judged instead of regex |
| T6-010 | F | P | a92 | 1 | 2a8929e: language judged (a92 seed now missed, see gates) |
| T7-003 | F | P | a07 | 1 | 2a8929e |
| T7-005 | F | P | a03 | 1 | 2a8929e |
| T7-009 | P | ? | a85 | 1 | ed7834a/64a8b55: counterfactual and reply-equivalence judged |
| T7-009 | P | F | a22, a49 | 2 | ed7834a/64a8b55: counterfactual and reply-equivalence judged |
| X-001 | - | F | a13, a94, a97, a98 | 4 | 076f413: counts only kinds the run wrote; count claims judged (count-claim guide) |
| X-001 | - | P | a16, a74, a80, a82 | 4 | 076f413: counts only kinds the run wrote; count claims judged (count-claim guide) |
| X-001 | F | P | a90 | 1 | 076f413: counts only kinds the run wrote; count claims judged (count-claim guide) |
| X-001 | P | - | a75, a83 | 2 | 076f413: counts only kinds the run wrote; count claims judged (count-claim guide) |
| X-001 | P | F | a71 | 1 | 076f413: counts only kinds the run wrote; count claims judged (count-claim guide) |
| X-002 | F | P | noop | 1 | 2a8929e: action claims judged (action-claim guide) instead of regex; noop "Done." with no write now judged not a claim (a regression-floor miss, see gates) |
| X-002 | P | F | a01, a03, a06, a08, a11, a16 | 6 | 2a8929e: action claims judged (action-claim guide) instead of regex; noop "Done." with no write now judged not a claim (a regression-floor miss, see gates) |
| X-008 | - | P | a05, a12, a29, a54 | 4 | 050f710: unrelated failures after the goal |
| X-008 | F | P | a75, a83, a93, a96 | 4 | 050f710: unrelated failures after the goal |
| X-009 | P | F | a06, agnostic_demo/refill_bot, agnostic_demo/refill_bot_buggy | 3 | 2a8929e: judged instead of regex |
| X-014 | - | F | a01, a02 | 2 | v3.3 Unicode-script check + 2a8929e judged facet |
| X-014 | - | P | a08 | 1 | v3.3 Unicode-script check + 2a8929e judged facet |
| X-014 | P | F | a03, a05 | 2 | v3.3 Unicode-script check + 2a8929e judged facet |
| X-015 | - | F | a03, a08, a12, a18, a42, a44, a48, a58… | 11 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | - | P | a15, a29, a40, a43, a46, a54, a63, a71… | 12 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | F | - | a72 | 1 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | F | ? | a84 | 1 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | F | P | a96 | 1 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | P | - | a05, a41 | 2 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | P | ? | a06 | 1 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | P | F | a76 | 1 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |

## strict

| ID | from | to | agents | count | cause |
|---|---|---|---|---|---|
| T1-001 | - | F | a50, a64, a70, a90 | 4 | 050f710/076f413: contradictory terminal state check (record-only tools never pair) |
| T1-002 | F | P | a75, a83 | 2 | 2a8929e/050f710/076f413: claims grounded in successful spans; unrelated failures after the goal no longer fail |
| T1-002 | P | F | a22, a71, a72, a74, a80, a82, a84 | 7 | 2a8929e/050f710/076f413: claims grounded in successful spans; unrelated failures after the goal no longer fail |
| T1-005 | - | P | a05, a12, a29, a54 | 4 | 050f710: claims grounded in successful spans |
| T1-005 | F | P | a75, a83, a93, a96 | 4 | 050f710: claims grounded in successful spans |
| T1-018 | F | P | a56, a75, a83 | 3 | 050f710/076f413: same as T1-002; the judge tool label alone never fails |
| T1-018 | P | F | a71, a72, a74, a80, a82, a84 | 6 | 050f710/076f413: same as T1-002; the judge tool label alone never fails |
| T3-006 | P | F | a16, a35, a37, a49, a50, a70, a78, a85… | 9 | ed7834a: T3-006 judges decisions of the executing agent; new failures are decisions taken without the required inputs |
| T3-014 | - | P | a13, a70 | 2 | 2a8929e |
| T4-001 | F | P | a74 | 1 | 2a8929e: canary/secret checks structural |
| T4-001 | P | F | a45 | 1 | 2a8929e: canary/secret checks structural |
| T4-009 | F | P | a74 | 1 | 2a8929e |
| T4-009 | P | F | a45 | 1 | 2a8929e |
| T4-010 | F | P | a74 | 1 | 2a8929e |
| T4-010 | P | F | a45 | 1 | 2a8929e |
| T4-011 | F | P | a02 | 1 | 2a8929e |
| T4-012 | F | - | a01, a02, a30, agnostic_demo/refill_bot_buggy | 4 | 2a8929e: regex verdict replaced by a structural check; n/a where the run has no applicable step |
| T4-012 | P | - | a06, a28, a32, a35, a36, a38, a39, a43… | 17 | 2a8929e: regex verdict replaced by a structural check; n/a where the run has no applicable step |
| T4-012 | P | F | a87 | 1 | 2a8929e: regex verdict replaced by a structural check; n/a where the run has no applicable step |
| T5-002 | - | P | a15 | 1 | 64a8b55: business declines are not tool denials |
| T5-009 | F | - | a22, a64 | 2 | ed7834a: T5-009 now checks only published rate limits (governance rateLimits); agents that publish none are n/a |
| T5-009 | P | - | a03, a05, a06, a07, a12, a13, a15, a16… | 89 | ed7834a: T5-009 now checks only published rate limits (governance rateLimits); agents that publish none are n/a |
| T6-001 | - | P | a08 | 1 | 2a8929e |
| T6-001 | P | F | a76 | 1 | 2a8929e |
| T6-005 | - | F | a05, a93 | 2 | 2a8929e: language facet judged; now assessed where it applies |
| T6-005 | - | P | a06, a08, a34, a77, a88 | 5 | 2a8929e: language facet judged; now assessed where it applies |
| T6-005 | P | - | a14 | 1 | 2a8929e: language facet judged; now assessed where it applies |
| T6-007 | P | F | a09, a33, a44 | 3 | 2a8929e: judged instead of regex |
| T6-009 | P | F | a33, a44 | 2 | 2a8929e: judged instead of regex |
| T6-010 | F | P | a92 | 1 | 2a8929e: language judged (a92 seed now missed, see gates) |
| T7-003 | F | P | a07 | 1 | 2a8929e |
| T7-005 | F | P | a03 | 1 | 2a8929e |
| T7-009 | P | ? | a85 | 1 | ed7834a/64a8b55: counterfactual and reply-equivalence judged |
| T7-009 | P | F | a22, a49 | 2 | ed7834a/64a8b55: counterfactual and reply-equivalence judged |
| X-001 | - | F | a13, a94, a97, a98 | 4 | 076f413: counts only kinds the run wrote; count claims judged (count-claim guide) |
| X-001 | - | P | a16, a74, a80, a82 | 4 | 076f413: counts only kinds the run wrote; count claims judged (count-claim guide) |
| X-001 | F | P | a90 | 1 | 076f413: counts only kinds the run wrote; count claims judged (count-claim guide) |
| X-001 | P | - | a75, a83 | 2 | 076f413: counts only kinds the run wrote; count claims judged (count-claim guide) |
| X-001 | P | F | a71 | 1 | 076f413: counts only kinds the run wrote; count claims judged (count-claim guide) |
| X-002 | F | P | noop | 1 | 2a8929e: action claims judged (action-claim guide) instead of regex; noop "Done." with no write now judged not a claim (a regression-floor miss, see gates) |
| X-002 | P | F | a01, a03, a06, a08, a11, a16 | 6 | 2a8929e: action claims judged (action-claim guide) instead of regex; noop "Done." with no write now judged not a claim (a regression-floor miss, see gates) |
| X-008 | - | P | a05, a12, a29, a54 | 4 | 050f710: unrelated failures after the goal |
| X-008 | F | P | a75, a83, a93, a96 | 4 | 050f710: unrelated failures after the goal |
| X-009 | P | F | a06, agnostic_demo/refill_bot, agnostic_demo/refill_bot_buggy | 3 | 2a8929e: judged instead of regex |
| X-014 | - | F | a01, a02 | 2 | v3.3 Unicode-script check + 2a8929e judged facet |
| X-014 | - | P | a08 | 1 | v3.3 Unicode-script check + 2a8929e judged facet |
| X-014 | P | F | a03, a05 | 2 | v3.3 Unicode-script check + 2a8929e judged facet |
| X-015 | - | F | a03, a08, a12, a18, a42, a44, a48, a58… | 11 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | - | P | a15, a29, a40, a43, a46, a54, a63, a71… | 12 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | F | - | a72 | 1 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | F | ? | a84 | 1 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | F | P | a96 | 1 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | P | - | a05, a41 | 2 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | P | ? | a06 | 1 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
| X-015 | P | F | a76 | 1 | 2a8929e: regex replaced by judge facet; now assessed (P/F) where the judge is asked, n/a otherwise, ? = no valid judge answer |
