#!/bin/sh
cd "$(dirname "$0")" || exit 1
OUT=results_ngspice42.txt
echo "ngspice: $(ngspice --version | grep -m1 ngspice)" > $OUT
for f in D1_gpio_drive D2_input_injection D3_por_ramp D4_supply_current_f; do
  echo "=== $f" >> $OUT
  ngspice -b $f.cir 2>&1 | grep -E "^(v\(|i\(|t_release|[0-9]+\s)" >> $OUT
done
