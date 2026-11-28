#!/usr/bin/env bash
# Runner for the agentest composite GitHub Action (action.yml). It also works outside GitHub
# Actions: every input is an AGENTEST_* environment variable, and GITHUB_OUTPUT /
# GITHUB_STEP_SUMMARY are optional. Inputs are never evaluated as shell code.
set -uo pipefail

fmt="${AGENTEST_FORMAT:-md}"
case "$fmt" in
  md|json|junit|sarif|html|csv) ;;
  *) echo "::error::agentest action: format must be one of md, json, junit, sarif, html, csv (got '$fmt')"; exit 2 ;;
esac
case "$fmt" in
  junit) ext=xml ;;
  *) ext="$fmt" ;;
esac
report="${AGENTEST_REPORT:-}"
[ -n "$report" ] || report="agentest-report.$ext"

comment_mode="${AGENTEST_PR_COMMENT:-false}"
case "$comment_mode" in
  false|true|summary) ;;
  *) echo "::error::agentest action: pr-comment must be one of false, true, summary (got '$comment_mode')"; exit 2 ;;
esac

# The inputs-derived arguments, shared by the report run and the optional verdicts run for the PR comment.
common=()

if [ -n "${AGENTEST_OTLP:-}" ]; then
  shopt -s nullglob globstar
  files=()
  # Split on spaces and new lines, then expand each glob without evaluating anything else.
  read -r -d '' -a patterns <<< "$AGENTEST_OTLP" || true
  for pattern in "${patterns[@]}"; do
    matches=( $pattern )
    if [ "${#matches[@]}" -eq 0 ] || [ ! -e "${matches[0]}" ]; then
      echo "::error::agentest action: no OTLP trace file matches '$pattern'"
      exit 2
    fi
    files+=( "${matches[@]}" )
  done
  shopt -u nullglob globstar
  common+=(--otlp "${files[@]}")
  [ -z "${AGENTEST_CARD:-}" ] || common+=(--card "$AGENTEST_CARD")
  [ -z "${AGENTEST_TOOLS:-}" ] || common+=(--tools "$AGENTEST_TOOLS")
else
  common+=(--agents "${AGENTEST_AGENTS:-agents}")
  [ -z "${AGENTEST_AGENT:-}" ] || common+=(--agent "$AGENTEST_AGENT")
fi
[ -z "${AGENTEST_IDS:-}" ] || common+=(--ids "$AGENTEST_IDS")
[ -z "${AGENTEST_MODE:-}" ] || common+=(--mode "$AGENTEST_MODE")
[ -z "${AGENTEST_CONFIG:-}" ] || common+=(--config "$AGENTEST_CONFIG")

args=(std run --format "$fmt" --out "$report" "${common[@]}")

fail_on_fail="${AGENTEST_FAIL_ON_FAIL:-true}"
if [ "$fail_on_fail" = "true" ]; then
  args+=(--strict)
fi

log="$(mktemp)"
echo "+ agentest ${args[*]}"
agentest "${args[@]}" 2>&1 | tee "$log"
code="${PIPESTATUS[0]}"

totals="$(grep -E '^total: ' "$log" | tail -n 1 || true)"
passed="$(sed -nE 's/^total: ([0-9]+) pass.*/\1/p' <<< "$totals")"
failed="$(sed -nE 's/^total: [0-9]+ pass, ([0-9]+) fail.*/\1/p' <<< "$totals")"
na="$(sed -nE 's/^total: [0-9]+ pass, [0-9]+ fail, ([0-9]+) n\/a.*/\1/p' <<< "$totals")"

# Optional PR comment (off by default): keep the verdicts as JSON and the reproduce command for the comment step.
# Judging is offline and deterministic, so a second run costs a moment and needs no network.
comment_dir=""
if [ "$comment_mode" != "false" ]; then
  comment_dir="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/agentest-comment.XXXXXX")"
  if agentest std run --format json --out "$comment_dir/verdicts.json" "${common[@]}" > /dev/null 2>&1 || [ -s "$comment_dir/verdicts.json" ]; then
    printf '%q ' agentest std run "${common[@]}" --format md > "$comment_dir/command.txt"
  else
    echo "::warning::agentest action: could not produce the verdicts for the PR comment (see the step log)"
    rm -f "$comment_dir/verdicts.json"
  fi
fi

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  {
    echo "exit-code=$code"
    echo "passed=${passed:-0}"
    echo "failed=${failed:-0}"
    echo "not-applicable=${na:-0}"
    echo "report=$report"
    echo "comment-dir=$comment_dir"
  } >> "$GITHUB_OUTPUT"
fi

if [ "${AGENTEST_JOB_SUMMARY:-true}" = "true" ] && [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### AiEnsured agentest"
    echo
    if [ -n "$totals" ]; then echo "\`$totals\`"; else echo "agentest exited with code $code (see the step log)."; fi
    echo
    if [ "$fmt" = "md" ] && [ -f "$report" ]; then cat "$report"; echo; fi
  } >> "$GITHUB_STEP_SUMMARY"
fi

rm -f "$log"
exit "$code"
