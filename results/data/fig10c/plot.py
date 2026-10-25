import os
os.system('rm -rf logs')
os.system('./extract_raw_logs.sh')
os.system('python3 plot_ping_latency_and_dilation.py')
