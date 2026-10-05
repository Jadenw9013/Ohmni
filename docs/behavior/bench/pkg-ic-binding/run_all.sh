#!/bin/sh
cd "$(dirname "$0")" || exit 1
OUT=results_ngspice42.txt
echo "ngspice: $(ngspice --version | grep -m1 ngspice)" > $OUT
for f in P1_tj_steady P2_thermal_via_parallel P3_lead_resonance P4_supply_droop; do
  echo "=== $f" >> $OUT
  ngspice -b $f.cir 2>&1 | grep -E "^(v\(|f[0-9]|peak_)" >> $OUT
done
