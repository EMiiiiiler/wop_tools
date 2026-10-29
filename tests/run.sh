#!/bin/sh
# run the regression tests (no compiler needed)
cd "$(dirname "$0")/.." && python3 -m pytest -q tests "$@"
