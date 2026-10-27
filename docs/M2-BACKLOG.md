# M2 backlog — `v0.3.0`

> **Historical (pre-v3).** This page describes code that was removed in v3.1.0; it is kept for the record. The
> implementation is at the `v1.0.0` / `v2.0.0` tags. Current docs: [User Guide](USER-GUIDE.md), [Author Guide](AUTHOR-GUIDE.md).

Full **privacy** pack (8 catalogue IDs).

## Tasks

1. [x] Extend Env (profiles, tenants, session_tenant_id, files, exports, emails, consent, post_revoke_share_calls)
2. [x] Privacy tools on ToolGateway (soft/hard delete, disclose_*, tenant.update_contact, send_email, export_*, consent, share_partner, search_users)
3. [x] CaseSpec registry entries for all 8 privacy IDs
4. [x] CLI `--suite privacy`
5. [x] Parametrized pytest Pass golden / Fail broken
6. [x] Functional suite regression still green
7. [ ] GitHub Actions *(deferred — no workflow OAuth scope)*

## IDs

| ID | Status |
|:---|:-------|
| T1-016 | done |
| T2-005 | done |
| T3-008 | done |
| T4-009 | done |
| T5-004 | done |
| T5-011 | done |
| T6-004 | done |
| T7-014 | done |

## Acceptance

- [x] `agentest run --suite privacy --agent golden` exit 0
- [x] `agentest run --suite privacy --agent broken` exit non-zero
- [x] `agentest run --suite functional --agent golden` exit 0
- [x] pytest green
