#!/bin/bash -eu

cd "$SRC/agentdeck"

# The fuzz targets import the loaders directly, so the repo root has to be
# importable without installing the tray/GUI extras.
export PYTHONPATH="$SRC/agentdeck"

for fuzzer in fuzz/fuzz_*.py; do
  compile_python_fuzzer "$fuzzer"
done
