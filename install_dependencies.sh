#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-${PROJECT_DIR}/.venv}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "Error: ${PYTHON_BIN} was not found. Install Python 3.10 or newer." >&2
    exit 1
fi

"${PYTHON_BIN}" - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit(
        f"Python 3.10 or newer is required; found {sys.version.split()[0]}"
    )
print(f"Using Python {sys.version.split()[0]}")
PY

if [[ ! -d "${VENV_DIR}" ]]; then
    echo "Creating virtual environment: ${VENV_DIR}"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
else
    echo "Using existing virtual environment: ${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "${PROJECT_DIR}/requirement.txt"
"${VENV_DIR}/bin/python" -m ipykernel install \
    --prefix "${VENV_DIR}" \
    --name chronos-artifact \
    --display-name "Python (Chronos Artifact)"

echo
echo "Dependencies installed successfully."
echo "Run the notebook with:"
echo "  source \"${VENV_DIR}/bin/activate\""
echo "  cd \"${PROJECT_DIR}\""
echo "  jupyter notebook plot.ipynb"
echo "Select the 'Python (Chronos Artifact)' kernel if prompted."
