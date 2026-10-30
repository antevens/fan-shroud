#!/bin/bash
#
# Recreates the project venv in .venv from the pinned requirements.txt.

set -euo pipefail

function main() {
  local repo_dir
  repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

  python3 -m venv --clear "${repo_dir}/.venv"
  "${repo_dir}/.venv/bin/pip" install --no-input --disable-pip-version-check \
    -r "${repo_dir}/requirements.txt"
}

main "$@"
