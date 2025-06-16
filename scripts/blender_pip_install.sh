#!/usr/bin/env bash

BLENDER_PYTHON="${BLENDER_PYTHON:-$HOME/Applications/blender/blender-4.3.2-linux-x64/4.3/python/bin/python3.11}"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <package> [--python <python-path>]"
    exit 1
fi

PACKAGE="$1"
shift

# Allow override of python binary via --python argument
while [[ $# -gt 0 ]]; do
    case "$1" in
        --python)
            BLENDER_PYTHON="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

if [ ! -x "$BLENDER_PYTHON" ]; then
    echo "Python binary not found: $BLENDER_PYTHON"
    exit 1
fi

"$BLENDER_PYTHON" -m ensurepip
"$BLENDER_PYTHON" -m pip install --upgrade pip
"$BLENDER_PYTHON" -m pip install "$PACKAGE"
