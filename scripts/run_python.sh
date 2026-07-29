#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_dir/.." && pwd)

if [ -z "${PYTHONPYCACHEPREFIX:-}" ]; then
    PYTHONPYCACHEPREFIX="$repository_root/.cache/pycache"
    export PYTHONPYCACHEPREFIX
fi

exec "${PYTHON_BIN:-python3}" "$@"
