#!/usr/bin/env bash
#
# Automates the Chronos-Agent experiment startup sequence:
#   core -> gnb -> ue -> persistue -> globalsc -> proxy -> UE start signal
# polling logs/pod status after each stage instead of watching them by hand.
#
# Must be run on the controller VM (10.2.1.2); it operates on the
# chronos-auto-deploy checkout it lives in. Component counts are read
# from values.yaml (numberProxyNodes/numberGNB/numberUE), so this scales from
# a single-gNB/UE test cluster up to clusters with thousands of gNB/UE
# without changes.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

# ---------- per-step check/diagnostic functions ----------

check_cores_ready() {
    seq 0 $((NUM_CORES - 1)) | parallel -j "$PARALLEL_JOBS" --halt now,fail=1 \
        'kubectl logs -c core core-{} 2>/dev/null | grep -q "AMF initialize...done"'
}
diag_cores() { kubectl get pods --no-headers 2>/dev/null | grep '^core-'; }

check_gnb_connected() {
    local count
    count=$(./core-logs.sh 2>/dev/null | grep "Total gNB count is" | awk '{print $NF}')
    [[ "$count" == "$NUM_GNB" ]]
}
diag_gnb_connected() { ./core-logs.sh 2>&1; }

check_proxies_ready() {
    local running connected
    running=$(kubectl get pods --no-headers 2>/dev/null | awk '$1 ~ /^proxy-/ && $3=="Running"' | wc -l)
    connected=$(l globalsc 2>/dev/null | grep -oP 'New proxy connected: ID \K[0-9]+' | sort -u | wc -l)
    [[ "$running" -eq "$NUM_PROXY" && "$connected" -eq "$NUM_PROXY" ]]
}
diag_proxies() {
    kubectl get pods --no-headers 2>/dev/null | grep '^proxy-'
    l globalsc 2>/dev/null | grep "New proxy connected: ID"
}

check_gnb_growth() {
    local count
    count=$(l "gnb-$GNB_N" 2>/dev/null | wc -l)
    (( count >= GNB_BASELINE * GROWTH_MULTIPLIER ))
}
diag_gnb_growth() { echo "gnb-$GNB_N baseline=$GNB_BASELINE current=$(l "gnb-$GNB_N" 2>/dev/null | wc -l)"; }

# ---------- straggler remediation (some UEs never attach, at scale) ----------
#
# At large scale a few dozen UEs out of thousands can fail to attach. By the
# time natural attach has plateaued for a full PLATEAU_WINDOW, "never
# received the start signal" (restart.sh's StartSignal tier) is not a
# plausible explanation - ue-start.sh/start.sh already broadcast it to every
# UE 10x right at the start. And RACH failures are a strict subset of Ping
# failures (no data plane is possible without RACH succeeding first), while
# both tiers apply the exact same fix (pkill -9 nr-uesoftmodem to force a
# restart). So Ping alone catches everything RACH would and more, with no
# need to run RACH separately. Tearing down the whole experiment over a
# handful of stragglers is wasteful at this scale, so instead: let natural
# attach run its course, then keep re-running Ping until it stops improving
# or the remediation deadline hits.

PLATEAU_WINDOW="${PLATEAU_WINDOW:-600}"             # seconds of no UPF growth before calling it plateaued
MONITOR_POLL_INTERVAL="${MONITOR_POLL_INTERVAL:-30}" # slower than POLL_INTERVAL - core-logs.sh gets expensive at scale
STUCK_ROUND_LIMIT="${STUCK_ROUND_LIMIT:-3}"          # consecutive no-improvement Ping rounds before giving up on stragglers

get_upf_count() {
    ./core-logs.sh 2>/dev/null | grep "Total UPF count is" | awk '{print $NF}'
}

# Polls the UPF (attached-UE) count until it either reaches NUM_UE, goes
# PLATEAU_WINDOW seconds with no increase, or the remediation deadline
# arrives. Sets PLATEAU_STATUS to success/plateau/deadline and PLATEAU_COUNT
# to the last observed count - never dies, since a plateau or deadline is an
# expected outcome here, not a script failure.
wait_for_upf_plateau_or_success() {
    local count last_increase now new_count
    count=$(get_upf_count)
    last_increase=$(date +%s)
    log "Monitoring UE attach progress ($count/$NUM_UE UPF sessions)"
    while true; do
        if [[ "$count" == "$NUM_UE" ]]; then
            PLATEAU_STATUS="success"; PLATEAU_COUNT="$count"; return
        fi
        now=$(date +%s)
        if (( now >= REMEDIATION_DEADLINE )); then
            log "Remediation deadline reached ($count/$NUM_UE UPF sessions)"
            PLATEAU_STATUS="deadline"; PLATEAU_COUNT="$count"; return
        fi
        if (( now - last_increase >= PLATEAU_WINDOW )); then
            log "UE attach plateaued at $count/$NUM_UE UPF sessions (no change for ${PLATEAU_WINDOW}s)"
            PLATEAU_STATUS="plateau"; PLATEAU_COUNT="$count"; return
        fi
        sleep "$MONITOR_POLL_INTERVAL"
        new_count=$(get_upf_count)
        if [[ "$new_count" != "$count" ]]; then
            log "UE attach progress: $new_count/$NUM_UE UPF sessions"
            last_increase=$(date +%s)
        fi
        count="$new_count"
    done
}

# Runs one restart.sh tier with Kill=Yes (a single pass both reports and
# fixes whichever UEs are currently failing that tier's check), logs its
# output, and sets FAILCOUNT to how many UEs it acted on.
run_restart_tier() {
    local tier="$1" out
    log "Running restart.sh $tier Yes"
    out=$(./restart.sh "$tier" Yes)
    echo "$out"
    FAILCOUNT=$(grep -c '^No ' <<< "$out")
    log "restart.sh $tier: $FAILCOUNT UE(s) affected"
}

# ---------- run the sequence ----------

log "Experiment scale: cores=$NUM_CORES gNB=$NUM_GNB UE=$NUM_UE proxies=$NUM_PROXY"

log "Removing oversized subscribers.bson (excluded from git, must not exist for helm)"
rm -f core/docker/open5gs/subscribers.bson

start_component core
wait_for "all cores ready (AMF initialize...done)" check_cores_ready diag_cores

start_component gnb
wait_for "all gNB connected to core" check_gnb_connected diag_gnb_connected

start_component ue
kubectl rollout status statefulset/ue --timeout="${TIMEOUT}s" || die "UE StatefulSet did not become ready within ${TIMEOUT}s"

log "Sleeping 10s before starting persistue/globalsc"
sleep 10

start_component persistue
start_component globalsc
REMEDIATION_DEADLINE=$(( $(date +%s) + 2*60*60 ))
wait_for "globalsc stabilized (Elapsed/Dilation factor lines, 1<=factor<3)" check_globalsc_stable diag_globalsc

GNB_N=$((RANDOM % NUM_GNB))
GNB_BASELINE=$(l "gnb-$GNB_N" 2>/dev/null | wc -l)
(( GNB_BASELINE == 0 )) && GNB_BASELINE=1
log "Sampling gnb-$GNB_N as a growth indicator, baseline=$GNB_BASELINE log lines"

start_component proxy
wait_for "all proxies running and connected to globalsc" check_proxies_ready diag_proxies
wait_for "gnb-$GNB_N log growth >= ${GROWTH_MULTIPLIER}x baseline" check_gnb_growth diag_gnb_growth

log "Sending UE start signal (ue-start.sh, then start.sh x10 with no wait between - some UEs miss the message at larger scales)"
./ue-start.sh || die "ue-start.sh failed"
for i in $(seq 1 10); do
    bash start.sh || die "start.sh failed (attempt $i)"
done

log "Letting UE attach happen naturally before considering remediation (remediation deadline: 2h from globalsc start)"
wait_for_upf_plateau_or_success

if [[ "$PLATEAU_STATUS" == "plateau" ]]; then
    log "Natural attach plateaued at $PLATEAU_COUNT/$NUM_UE - beginning restart.sh Ping remediation"

    stuck_rounds=0
    prev_failcount=-1
    while [[ "$PLATEAU_STATUS" == "plateau" ]]; do
        run_restart_tier Ping
        if (( FAILCOUNT == 0 )); then
            break
        fi
        if (( prev_failcount >= 0 && FAILCOUNT >= prev_failcount )); then
            stuck_rounds=$((stuck_rounds + 1))
        else
            stuck_rounds=0
        fi
        prev_failcount=$FAILCOUNT
        if (( stuck_rounds >= STUCK_ROUND_LIMIT )); then
            log "No improvement in Ping-tier failures for $STUCK_ROUND_LIMIT consecutive rounds ($FAILCOUNT UE still stuck) - giving up on stragglers this run"
            break
        fi
        wait_for_upf_plateau_or_success
    done
fi

FINAL_COUNT=$(get_upf_count)
if [[ "$FINAL_COUNT" == "$NUM_UE" ]]; then
    log "Experiment startup complete: $NUM_CORES core(s), $NUM_GNB gNB, $NUM_UE UE, $NUM_PROXY proxy all up and connected."
else
    log "Experiment startup finished with $FINAL_COUNT/$NUM_UE UE connected ($((NUM_UE - FINAL_COUNT)) unrecovered)."
    log "Experiment is left running (not torn down). Inspect stragglers manually, e.g. ./restart.sh Ping No"
fi
