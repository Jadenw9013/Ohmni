#!/bin/sh
# run every BEH-REG-BUCK-DCS bench with ngspice-42; results appended to results_ngspice42.txt (this directory only)
cd "$(dirname "$0")" || exit 1
OUT=results_ngspice42.txt
: > $OUT
echo "ngspice: $(ngspice --version | grep -m1 ngspice)" >> $OUT
for f in B1_steady_state B3_load_step B4_tps62130_variant B5_line_regulation; do
  echo "=== $f" >> $OUT
  ngspice -b $f.cir 2>&1 | grep -iE "^(fsw|dil|vavg|eta|under_mV|over_mV|droop_dc_mV|v6|v12|v17|pin_avg|pout_avg)\s*=" >> $OUT
done
# B2: load sweep (RL, TSTOP, TAVG0 chosen so that >= 20 switching cycles or pulses are averaged)
for pair in "330:200u:100u" "33:100u:50u" "6.6:80u:40u" "3.3:80u:40u"; do
  RL=${pair%%:*}; rest=${pair#*:}; TS=${rest%%:*}; TA=${rest#*:}
  sed -e "s/@RL@/$RL/g" -e "s/@TSTOP@/$TS/g" -e "s/@TAVG0@/$TA/g" B2_efficiency.cir > _b2_tmp.cir
  echo "=== B2 RL=$RL ohm" >> $OUT
  ngspice -b _b2_tmp.cir 2>&1 | grep -iE "^(eta|pin_avg|pout_avg|vavg|fsw)\s*=" >> $OUT
done
rm -f _b2_tmp.cir
