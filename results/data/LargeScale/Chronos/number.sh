#!/bin/bash
NUM_UE=0
for i in $1/ue-*-dp.log; do
    cat $i | grep "rtt=" > /dev/null && ((NUM_UE++))
done

echo $NUM_UE
