#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "USE: ./restart.sh <Check type=StartSignal/RACH/Ping> <Kill=Yes/No>"
    exit 1
fi

EXPERIMENT=$(yq '.numberUE' values.yaml)
CHECK=$1

KILLER="NO"
[ "$2" == "Yes" ] && {
    echo "Will be killing pods"
    KILLER="YES"
}

check_ue_startsignal() {
    kubectl logs -c ue "ue-$1" | grep "Calling sched_setscheduler" > /dev/null ||  {
        echo "No start signal for UE $1"
        if [ "$KILLER" == "YES" ]; then
            IP=$(kubectl get pod "ue-$1" -o=jsonpath='{.status.podIP}')
            echo hello > /dev/udp/$IP/12000
        fi
    }
}

check_ue_rach() {
    kubectl logs -c ue "ue-$1" | grep "accessStratumRelease" > /dev/null ||  {
        echo "No RACH from UE $1"
        if [ "$KILLER" == "YES" ]; then
            kubectl exec "ue-$1" -c ue -- pkill -9 nr-uesoftmodem
        fi
    }
}

check_ue_ping() {
    kubectl logs -c dp "ue-$1" | grep "Data plane is up" > /dev/null ||  {
        echo "No data plane from UE $1"
        if [ "$KILLER" == "YES" ]; then
            kubectl exec -it "ue-$1" -c ue -- pkill -9 nr-uesoftmodem
        fi
    }
}

export KILLER

if [ $CHECK == "StartSignal" ]; then
    echo "Running StartSignal test"
    export -f check_ue_startsignal
    seq 0 $(($EXPERIMENT - 1)) | parallel check_ue_startsignal
elif [ $CHECK == "RACH" ]; then
    echo "Running RACH test"
    export -f check_ue_rach
    seq 0 $(($EXPERIMENT - 1)) | parallel check_ue_rach
elif [ $CHECK == "Ping" ]; then
    echo "Running Ping / Data Plane test"
    export -f check_ue_ping
    seq 0 $(($EXPERIMENT - 1)) | parallel check_ue_ping
else
    echo "Unknown test $CHECK"
    echo "Aborting"
fi
