# Step 1: Edit values.yaml and change "numberGNBNodes"
# vary it from 1 to 90, in steps of: 1, 2, 5, 10, 20, 30, 50, 70, 90
usage: ./change_node.sh <num>
./change_node.sh 1
./change_node.sh 2
./change_node.sh 5
./change_node.sh 10
./change_node.sh 20
./change_node.sh 30
./change_node.sh 50
./change_node.sh 70
./change_node.sh 90

# Step 2: Run globalsc
s globalsc

# Step 3: Wait 1 minute

# Step 4: Collect the logs
l globalsc > "globalsc_<num nodes>.log"
l globalsc > "globalsc_1.log"
l globalsc > "globalsc_2.log"
l globalsc > "globalsc_5.log"
l globalsc > "globalsc_10.log"
l globalsc > "globalsc_20.log"
l globalsc > "globalsc_30.log"
l globalsc > "globalsc_50.log"
l globalsc > "globalsc_70.log"
l globalsc > "globalsc_90.log"

# Step 5: Stop globalsc
ns globalsc

# Step 6: Wait for the globalsc pod to not be running
p # should say "No resources found in default namespace."

#After all finish
python3 plot_dilation_vs_nodes.py