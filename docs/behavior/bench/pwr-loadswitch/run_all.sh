#!/bin/sh
cd "$(dirname "$0")" || exit 1
OUT=results_ngspice42.txt
echo "ngspice: $(ngspice --version | grep -m1 ngspice)" > $OUT
for f in L1_ron_drop L2_uvlo L3_current_limit; do
  echo "=== $f" >> $OUT
  ngspice -b $f.cir 2>&1 | grep -iE "^(vdrop|pd|dt|t_on|vout_at|vin_at|ishort|iok)" >> $OUT
done
