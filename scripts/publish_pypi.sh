#!/usr/bin/env bash
# Upload the built agentest-ai 3.3.2 artifacts to PyPI. Needs PYPI_API_TOKEN in the environment.
# The token is passed to twine via env vars only; it is never echoed or written to disk.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PYPI_API_TOKEN:?PYPI_API_TOKEN is not set (export it first; it will not be printed)}"
shopt -s nullglob
files=(dist/agentest_ai-3.3.2*)
if [ ${#files[@]} -eq 0 ]; then echo "no dist/agentest_ai-3.3.2* artifacts; build first (python -m build)" >&2; exit 1; fi
python -m twine check "${files[@]}"
set +x
TWINE_USERNAME=__token__ TWINE_PASSWORD="$PYPI_API_TOKEN" TWINE_NON_INTERACTIVE=1 \
  python -m twine upload --disable-progress-bar "${files[@]}"
echo "uploaded: ${files[*]}  ->  https://pypi.org/project/agentest-ai/3.3.2/"
