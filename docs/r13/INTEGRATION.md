# r13 integration

Unreleased. Not tagged and not released. This branch is not for merge.

Stage A is W0 plus the detector modules below, adapted to `Detector` / `register()`. #47 is not included. #53, #54 and #55 wait for new heads.

| Source | Head | What landed |
|---|---|---|
| W0 (#50) | `25d5981` | Universal checks split into detector modules. Verdict text of the built-ins is unchanged. |
| #46 | `4fcca3a` | T1-001 state outcome |
| #48 | `7b3a45f` | T6-001 / T6-008 constraint memory |
| #49 | `c845fdf` | T1-006 / T1-011 / T2-003 object ledger |
| #51 | `222a009` | T2-001 / T2-013 closure-aware prerequisites |
| #52 | `8527b26` | T6-010 language block and T6-002 / T6-003 grounding |
| #55 | `1596904` | Hallucinated actions on T1-005, X-008, T1-018, T1-013, T5-012 |

#47 (`a275c39`) is left out. On the r12 re-recordings it raises T7-001 and T7-006 on a127, a133 and a151, and it restores T7-006 behaviour reverted in `e8ca4b3`. No included module imports it.

#53 and #54 are not on this branch. #59 waits until its CI is green.

The dev-label exclusion for the B_interpretive T1-006 and T1-011 cells is commit `f3fbb58` on this branch. Check logic is unchanged. Fresh-batch labels are not in this tree.

Scope, aggregation, thresholds and the n/a = miss rule are unchanged.
