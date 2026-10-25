import os
os.system('gunzip proxy-25.pcap.gz')
os.system('gunzip proxy-250.pcap.gz')
os.system('python3 analyse_proxy.py --csv-out "Chronos.csv" --out /dev/null proxy-25.pcap')
os.system('python3 analyse_proxy.py --csv-out "EMANE.csv" --out /dev/null proxy-250.pcap')
os.system('python3 plot-fig.py "Chronos.csv" "EMANE.csv"')
