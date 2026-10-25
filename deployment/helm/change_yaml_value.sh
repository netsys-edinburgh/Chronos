#!/bin/bash
# Usage: ./set_gnb_ue.sh 90
num=$1
sed -i "s/^\(numberGNB:\s*\).*/\1$num/; s/^\(numberUE:\s*\).*/\1$num/" values.yaml
export NUM_UE=$num
echo "numberGNB and numberUE in values.yaml set to $num"
echo "NUM_UE exported as $num"
