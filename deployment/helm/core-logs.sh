#!/bin/bash

NUM_CORES=$(yq '.numberProxyNodes' values.yaml)

TOTAL_GNB=0
TOTAL_UPF=0
for i in $(seq 0 $(($NUM_CORES - 1))); do
    GNBS=$(kubectl exec -c core "core-$i" -- bash -c "cat /core.log | grep \"Number of gNBs is now\" | awk -F ' ' '{ printf \$11 \"\n\" }'| tail -1")
    UPFS=$(kubectl exec -c core "core-$i" -- bash -c "cat /core.log | grep UPF | awk -F ' ' '{ print \$11 }' | tail -1")
    if [ "$GNBS" != "" ]; then
        TOTAL_GNB=$(($TOTAL_GNB + $GNBS))
    fi
    if [ "$UPFS" != "" ]; then
        TOTAL_UPF=$(($TOTAL_UPF + $UPFS))
    fi
    echo "Core $i has ${GNBS:-0} gNB, ${UPFS:-0} UPFs"
done
echo "Total gNB count is $TOTAL_GNB"
echo "Total UPF count is $TOTAL_UPF"
