#!/usr/bin/env bash
#
# Tears down a Chronos-Agent experiment in a specific, non-obvious order.
#
# globalsc controls the kernel module that drives node timing. At scale,
# tearing everything down concurrently can drop messages to/from globalsc,
# leaving nodes wedged with time not advancing. To avoid that:
#   1. Kill globalsc FIRST, on its own, and confirm it's fully gone.
#   2. Then tear down gnb and ue.
#   3. Then tear down proxy, core, persistue.
#   4. Wait for every gnb/ue/proxy/core/persistue pod to be fully removed. A
#      node can independently become "stuck" (the same kernel-timing issue
#      globalsc exists to prevent) before we ever get here, in which case its
#      pods will terminate forever - if that happens, briefly cycle globalsc
#      back up and down to unstick it, retrying a bounded number of times.
#   5. Bring globalsc back up alone and let it stabilize, as a final pass
#      to correct any timing drift left over from the teardown.
#   6. Tear globalsc down again.
#
# Must be run on the controller VM (10.2.1.2); it operates on the
# chronos-auto-deploy checkout it lives in.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

# The globalsc helm release deploys two pods: globalsc itself and irtt.
GLOBALSC_PODS=(globalsc irtt)

check_globalsc_gone() {
    local name
    for name in "${GLOBALSC_PODS[@]}"; do
        kubectl get pod "$name" >/dev/null 2>&1 && return 1
    done
    return 0
}
diag_globalsc_gone() {
    kubectl get pods --no-headers 2>/dev/null | grep -E '^(globalsc|irtt)\b' || echo "(no globalsc/irtt pods remaining)"
}

# Matches every gnb-*, ue-* (StatefulSet), proxy-*, core-* pod plus the
# single persistue pod, in one bulk query so this stays cheap at thousands
# of pods.
check_workload_pods_gone() {
    local remaining
    remaining=$(kubectl get pods --no-headers 2>/dev/null | awk '$1 ~ /^(gnb-|ue-|proxy-|core-)/ || $1=="persistue"' | wc -l)
    [[ "$remaining" -eq 0 ]]
}
diag_workload_pods_gone() {
    kubectl get pods --no-headers 2>/dev/null | awk '$1 ~ /^(gnb-|ue-|proxy-|core-)/ || $1=="persistue"'
}

STUCK_NODE_WAIT="${STUCK_NODE_WAIT:-120}"                 # seconds to wait for pods to terminate before assuming a node is stuck
STUCK_NODE_UNSTICK_ATTEMPTS="${STUCK_NODE_UNSTICK_ATTEMPTS:-3}"

# Polls check_workload_pods_gone for up to STUCK_NODE_WAIT seconds. Returns
# 0 if pods are gone, 1 if the wait expired first - never dies, since timing
# out here just means "maybe a node is stuck," not a script failure.
wait_briefly_for_workload_pods_gone() {
    local start now
    start=$(date +%s)
    while true; do
        check_workload_pods_gone && return 0
        now=$(date +%s)
        (( now - start >= STUCK_NODE_WAIT )) && return 1
        sleep "$POLL_INTERVAL"
    done
}

log "Tearing down globalsc FIRST (critical: prevents dropped timing messages from wedging nodes)"
stop_component globalsc
wait_for "globalsc/irtt pods fully removed from cluster" check_globalsc_gone diag_globalsc_gone

log "Tearing down gnb and ue"
stop_component gnb
stop_component ue

log "Tearing down proxy, core, persistue"
stop_component proxy
stop_component core
stop_component persistue

if ! wait_briefly_for_workload_pods_gone; then
    log "Pods still terminating after ${STUCK_NODE_WAIT}s - a node may be stuck. Attempting to unstick it by cycling globalsc."
    attempt=1
    unstuck=false
    while (( attempt <= STUCK_NODE_UNSTICK_ATTEMPTS )); do
        log "Unstick attempt $attempt/$STUCK_NODE_UNSTICK_ATTEMPTS: bringing globalsc up briefly"
        start_component globalsc
        wait_for "globalsc stabilized (Elapsed/Dilation factor lines, 1<=factor<3)" check_globalsc_stable diag_globalsc
        stop_component globalsc
        if wait_briefly_for_workload_pods_gone; then
            log "Pods finished terminating after unstick attempt $attempt"
            unstuck=true
            break
        fi
        attempt=$((attempt + 1))
    done
    if [[ "$unstuck" != true ]]; then
        diag_workload_pods_gone
        die "Pods still stuck terminating after $STUCK_NODE_UNSTICK_ATTEMPTS globalsc unstick attempts"
    fi
fi

log "Waiting 3 seconds for cluster to stabilise"
sleep 3

log "Restarting globalsc alone as a final timing-correction pass"
start_component globalsc
wait_for "globalsc stabilized (Elapsed/Dilation factor lines, 1<=factor<3)" check_globalsc_stable diag_globalsc

log "Tearing down globalsc (final)"
stop_component globalsc

log "Teardown complete."
