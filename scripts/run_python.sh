#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_dir/.." && pwd)

if [ -z "${PYTHONPATH:-}" ]; then
    PYTHONPATH="$repository_root/src"
else
    PYTHONPATH="$repository_root/src:$PYTHONPATH"
fi
export PYTHONPATH

if [ -z "${PYTHONPYCACHEPREFIX:-}" ]; then
    PYTHONPYCACHEPREFIX="$repository_root/.cache/pycache"
    export PYTHONPYCACHEPREFIX
fi

if [ -n "${PYTHON_BIN:-}" ]; then
    python_bin=$PYTHON_BIN
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    python_bin="$VIRTUAL_ENV/bin/python"
elif [ -x "$repository_root/.venv/bin/python" ]; then
    python_bin="$repository_root/.venv/bin/python"
else
    python_bin=python3
fi

exec "$python_bin" "$@"
