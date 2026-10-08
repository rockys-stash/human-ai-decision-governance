#!/usr/bin/env bash
# Re-runs every experiment reported in research/REPORT.md, then regenerates its tables and figures.
set -euo pipefail
cd "$(dirname "$0")/.."
# Single-threaded BLAS/OpenMP: avoids oversubscription when experiments run side by side.
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
for cfg in configs/e1_calibration.yaml configs/e2_regimes.yaml configs/e3_frontier.yaml \
           configs/e4_sensitivity.yaml configs/e5_shift.yaml; do
  echo "== $cfg"
  uv run governance run "$cfg"
done
uv run governance report
