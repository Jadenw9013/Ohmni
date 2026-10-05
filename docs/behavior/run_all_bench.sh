#!/bin/bash
# runs every bench netlist from its own directory, 60 s cap, writes a status table
out=/home/claude/behavior/bench_rerun.tsv; : > $out
find bench -name '*.cir' | sort | while read f; do
  d=$(dirname "$f"); b=$(basename "$f")
  log=$(cd "$d" && timeout 60 ngspice -b "$b" 2>&1); rc=$?
  err=$(echo "$log" | grep -i -E "error|singular|no such|fatal|timestep too small|aborted" | head -2 | tr '\n' ' ' | cut -c1-140)
  echo -e "$f\t$rc\t$err" >> $out
done
