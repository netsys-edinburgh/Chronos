#!/bin/bash
python3 analyze_globalsc_barrier_arrivals.py --csv 10k.csv --pdf /dev/null 10k-globalsc.pcap
python3 plot_globalsc.py 10k.csv
