#!/bin/bash
kubectl get pods -o wide | grep "ue-" | awk -F ' ' '{ print "echo hello > /dev/udp/" $6 "/12000" }' > start.sh