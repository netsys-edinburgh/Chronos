#!/bin/bash
mkdir logs
list='0 25000 30000 35000 40000 45000 50000 100000 500000'
for num in $list; do
  cp stress_raw/${num}stres*_2026-03-07_*/globalsc.log ./logs/globalsc-${num}.log
  cp stress_raw/${num}stres*_2026-03-07_*/ue-0-dp.log ./logs/ue-${num}.log
done
# also copy no stress
