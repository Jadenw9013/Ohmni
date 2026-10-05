#!/bin/sh
cd "$(dirname "$0")" || exit 1
OUT=results_ngspice42.txt
echo "ngspice: $(ngspice --version | grep -m1 ngspice)" > $OUT
for f in F1_spi_read_timing F2_program_current_droop; do
  echo "=== $f" >> $OUT
  ngspice -b $f.cir 2>&1 | grep -E "^(tcs_low|tces|peak_)" >> $OUT
done
