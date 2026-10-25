#!/usr/bin/env bash
#
# Shared helpers for run-experiment.sh / teardown-experiment.sh.
# Must be sourced, not executed directly.

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DEPLOY_DIR" || { echo "ERROR: could not enter deploy dir $DEPLOY_DIR"; exit 1; }

source ~/.chronos

# --- tunables (override via environment) ---
TIMEOUT="${TIMEOUT:-600}"                   # per-step wait timeout, seconds
POLL_INTERVAL="${POLL_INTERVAL:-3}"         # seconds between polls
GROWTH_MULTIPLIER="${GROWTH_MULTIPLIER:-5}" # gNB log growth factor required after proxy start
PARALLEL_JOBS="${PARALLEL_JOBS:-0}"         # 0 = GNU parallel default (one per core)

for dep in yq parallel kubectl; do
    command -v "$dep" >/dev/null 2>&1 || { echo "ERROR: required tool '$dep' not found on PATH"; exit 1; }
done

NUM_CORES=$(yq '.numberProxyNodes' values.yaml)
NUM_GNB=$(yq '.numberGNB' values.yaml)
NUM_UE=$(yq '.numberUE' values.yaml)
NUM_PROXY=$(yq '.numberProxyNodes' values.yaml)

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { log "ERROR: $*"; exit 1; }

# wait_for DESCRIPTION CHECK_FN [DIAG_FN]
# Polls CHECK_FN (a function returning 0/1) until it succeeds or TIMEOUT
# elapses, in which case DIAG_FN (if given) is run for debugging and the
# script aborts.
wait_for() {
    local desc="$1" check_fn="$2" diag_fn="${3:-}"
    local start elapsed
    start=$(date +%s)
    log "Waiting for: $desc (timeout ${TIMEOUT}s)"
    while true; do
        if "$check_fn"; then
            log "OK: $desc"
            return 0
        fi
        elapsed=$(( $(date +%s) - start ))
        if (( elapsed >= TIMEOUT )); then
            log "TIMEOUT after ${elapsed}s waiting for: $desc"
            if [[ -n "$diag_fn" ]]; then
                log "--- diagnostic output ---"
                "$diag_fn"
                log "--- end diagnostic ---"
            fi
            die "$desc did not complete within ${TIMEOUT}s"
        fi
        sleep "$POLL_INTERVAL"
    done
}

start_component() {
    local name="$1"
    log "Starting component: $name (s $name)"
    s "$name" || die "helm install failed for component '$name'"
}

stop_component() {
    local name="$1"
    log "Stopping component: $name (ns $name)"
    ns "$name" || log "WARNING: 'ns $name' failed (release may already be gone) - continuing"
}

# Shared globalsc-stabilization check: used both when starting an experiment
# and during teardown's final "correct any timing drift" pass.
check_globalsc_stable() {
    local logs
    mapfile -t logs < <(l globalsc 2>/dev/null | tail -5)
    (( ${#logs[@]} >= 5 )) || return 1
    local line factor
    for line in "${logs[@]}"; do
        [[ "$line" =~ ^Elapsed:\ [0-9]+,\ Dilation\ factor:\ ([0-9]+\.[0-9]+)$ ]] || return 1
        factor="${BASH_REMATCH[1]}"
        awk -v f="$factor" 'BEGIN{exit !(f>=1 && f<3)}' || return 1
    done
    return 0
}
diag_globalsc() { l globalsc 2>/dev/null | tail -20; }
