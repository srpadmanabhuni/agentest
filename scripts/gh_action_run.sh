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

args=(std run --format "$fmt" --out "$report")

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
  args+=(--otlp "${files[@]}")
  [ -z "${AGENTEST_CARD:-}" ] || args+=(--card "$AGENTEST_CARD")
  [ -z "${AGENTEST_TOOLS:-}" ] || args+=(--tools "$AGENTEST_TOOLS")
else
  args+=(--agents "${AGENTEST_AGENTS:-agents}")
  [ -z "${AGENTEST_AGENT:-}" ] || args+=(--agent "$AGENTEST_AGENT")
fi
[ -z "${AGENTEST_IDS:-}" ] || args+=(--ids "$AGENTEST_IDS")
[ -z "${AGENTEST_MODE:-}" ] || args+=(--mode "$AGENTEST_MODE")
[ -z "${AGENTEST_CONFIG:-}" ] || args+=(--config "$AGENTEST_CONFIG")

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

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  {
    echo "exit-code=$code"
    echo "passed=${passed:-0}"
    echo "failed=${failed:-0}"
    echo "not-applicable=${na:-0}"
    echo "report=$report"
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
