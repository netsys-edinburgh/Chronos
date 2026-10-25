#!/bin/bash

NUM_UES=$(yq '.numberUE' values.yaml)
NUM_PROXY=$(yq '.numberProxyNodes' values.yaml)

CAPTURE_SECONDS="${CAPTURE_SECONDS:-60}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/experiment_key}"
SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)
SSH_USER=root
REMOTE_BASE=/tmp
RUN_ID="$(date +'%F_%H-%M-%S.%N')-$$"
REMOTE_DIR="$REMOTE_BASE/save-logs-pcaps-$RUN_ID"
PCAP_STATUS=0

started_hosts=()
started_labels=()
started_pid_files=()
captures_stopped=0

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

run_ssh() {
    local host="$1"
    shift
    ssh "${SSH_OPTS[@]}" "${SSH_USER}@${host}" "$@"
}

run_scp() {
    local source="$1"
    local destination="$2"
    scp "${SSH_OPTS[@]}" "$source" "$destination"
}

start_remote_capture() {
    local host="$1"
    local label="$2"
    local remote_pcap="$REMOTE_DIR/$label.pcap"
    local remote_pid="$REMOTE_DIR/$label.pid"
    local remote_log="$REMOTE_DIR/$label.log"
    local remote_cmd

    remote_cmd="mkdir -p '$REMOTE_DIR' && { nohup tcpdump -i any -w '$remote_pcap' > '$remote_log' 2>&1 < /dev/null & echo \$! > '$remote_pid'; }"
    log "Starting pcap on $label ($host)"
    if run_ssh "$host" "$remote_cmd"; then
        started_hosts+=("$host")
        started_labels+=("$label")
        started_pid_files+=("$remote_pid")
    else
        log "WARNING: failed to start pcap on $label ($host)"
        PCAP_STATUS=1
    fi
}

stop_remote_captures() {
    local host i label pid_file stop_cmd

    if (( captures_stopped )); then
        return 0
    fi

    for i in "${!started_hosts[@]}"; do
        host="${started_hosts[$i]}"
        label="${started_labels[$i]}"
        pid_file="${started_pid_files[$i]}"
        stop_cmd="if [ -f '$pid_file' ]; then pid=\$(cat '$pid_file'); kill -INT \"\$pid\" 2>/dev/null || true; for _ in 1 2 3 4 5; do kill -0 \"\$pid\" 2>/dev/null || exit 0; sleep 1; done; kill -0 \"\$pid\" 2>/dev/null && exit 1 || exit 0; fi"
        log "Stopping pcap on $label ($host)"
        if ! run_ssh "$host" "$stop_cmd"; then
            log "WARNING: failed to stop pcap on $label ($host)"
            PCAP_STATUS=1
        fi
    done
    captures_stopped=1
}

copy_remote_pcap() {
    local host="$1"
    local label="$2"
    local source="${SSH_USER}@${host}:$REMOTE_DIR/$label.pcap"
    local destination="$DIR/pcaps/$label.pcap"

    log "Pulling $label pcap into $destination"
    if ! run_scp "$source" "$destination"; then
        log "WARNING: failed to pull pcap for $label ($host)"
        PCAP_STATUS=1
    fi
}

cleanup_pcaps() {
    stop_remote_captures || true
}

save_ue_log() {
    kubectl logs -c ue "ue-$1" > "$DIR/ue-$1-main.log"
    kubectl logs -c dp "ue-$1" > "$DIR/ue-$1-dp.log"
}

save_core_log() {
    kubectl exec -c core "core-$1" -- cat /core.log > "$DIR/core-$1.log"
}

trap cleanup_pcaps EXIT
trap 'cleanup_pcaps; exit 130' INT TERM

log "Starting pcap captures for $NUM_PROXY proxy node(s) and globalsc"
for i in $(seq 0 $(($NUM_PROXY - 1))); do
    start_remote_capture "10.3.$((i + 1)).1" "proxy-$i"
done
start_remote_capture "10.4.1.1" "globalsc"

log "Capturing traffic for ${CAPTURE_SECONDS}s"
sleep "$CAPTURE_SECONDS"

# Make a directory to store the logs and pcaps
DIR="${NUM_UES}_$( date +'%F_%H-%M-%S.%N')"
log "Creating output directory $DIR"
mkdir -p "$DIR/pcaps"

log "Stopping pcap captures"
stop_remote_captures

log "Pulling pcaps into $DIR/pcaps"
for i in $(seq 0 $(($NUM_PROXY - 1))); do
    copy_remote_pcap "10.3.$((i + 1)).1" "proxy-$i"
done
copy_remote_pcap "10.4.1.1" "globalsc"

export NUM_UES
export NUM_PROXY
export DIR

log "Saving UE logs into $DIR"
export -f save_ue_log
seq 0 $(($NUM_UES - 1)) | parallel save_ue_log

log "Saving core logs into $DIR"
export -f save_core_log
seq 0 $(($NUM_PROXY - 1)) | parallel save_core_log

log "Saving Global Slot Checker logs into $DIR/globalsc.log"
kubectl logs globalsc > "$DIR/globalsc.log"

log "Saving Kubernetes pod snapshot into $DIR/kubectl.log"
kubectl get pods -o wide > "$DIR/kubectl.log"

if (( PCAP_STATUS )); then
    log "Completed log collection in $DIR, but one or more pcap steps failed"
    exit 1
fi

log "Completed log and pcap collection in $DIR"
