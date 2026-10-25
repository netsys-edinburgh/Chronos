#!/usr/bin/env bash
# download_images.sh — build k0s airgap image bundles from values.yaml and
# ship them to every node in the cluster, so k0s's embedded containerd
# already has the images and never has to hit the registry itself.
#
# Runs automatically as the final step of master_install_k0.sh on the
# controller (ins0vm), right after k0s itself is installed. It is also
# meant to be run by hand afterwards: after editing values.yaml (e.g. via
# change_node.sh, or bumping an image tag), just re-run this script from
# ins0vm to push the update out. Takes no arguments; everything it needs
# comes from values.yaml sitting next to it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALUES="$SCRIPT_DIR/values.yaml"
KEY="$HOME/.ssh/experiment_key"
SSH_OPTS="-oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -oConnectTimeout=15 -i $KEY"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

log()  { echo "[download_images] $*"; }
fail() { echo "❌ FATAL(download_images): $*" >&2; exit 1; }
export -f log fail

[ -f "$VALUES" ] || fail "values.yaml not found at $VALUES"
[ -f "$KEY" ] || fail "experiment SSH key not found at $KEY (expected to be copied there by build_kernel.sh)"
command -v yq >/dev/null 2>&1 || fail "yq not found (expected to already be installed by master_install_k0.sh)"
command -v parallel >/dev/null 2>&1 || fail "GNU parallel not found (expected to already be installed before this script runs)"

CORE_IMG=$(yq '.coreImage' "$VALUES")
GLOBALSC_IMG=$(yq '.globalSCImage' "$VALUES")
GNB_IMG=$(yq '.gNBImage' "$VALUES")
PROXY_IMG=$(yq '.proxyImage' "$VALUES")
UE_IMG=$(yq '.ueImage' "$VALUES")
UEDP_IMG=$(yq '.ueDataPlaneImage' "$VALUES")
MONGO_IMG=$(yq '.mongoImage' "$VALUES")
PERSISTUE_IMG=$(yq '.persistueImage' "$VALUES")
N_GNB=$(yq '.numberGNBNodes' "$VALUES")
N_PROXY=$(yq '.numberProxyNodes' "$VALUES")

log "Images: core=$CORE_IMG globalsc=$GLOBALSC_IMG gnb=$GNB_IMG proxy=$PROXY_IMG ue=$UE_IMG ueDataPlane=$UEDP_IMG mongo=$MONGO_IMG persistue=$PERSISTUE_IMG"
log "Expected topology: $N_GNB ins-vm node(s), $N_PROXY proxy node(s), 1 globalsc node"

# Every node we expect to see in the cluster, except the controller itself
# (ins0vm, named "controller" in k8s — it doesn't run any of these pods, per
# k0s's own airgap docs: "controller nodes don't use it").
EXPECTED_NODES=()
for ((i = 1; i <= N_GNB; i++)); do EXPECTED_NODES+=("ins${i}vm"); done
for ((i = 0; i < N_PROXY; i++)); do EXPECTED_NODES+=("proxy-${i}"); done
EXPECTED_NODES+=("globalsc")

################################################################################
# Step 1/2: wait until every expected node (by name, not just count) has
# actually joined the cluster and is Ready. A node that never shows up isn't
# fatal -- after the timeout, drop it and distribute images to whichever
# nodes did make it. This is what makes it cheap to manually bolt a
# previously-failed node onto the cluster later and just re-run this script.
################################################################################
: "${JOIN_TIMEOUT:=1800}"    # seconds to wait for expected nodes to join + become Ready
: "${JOIN_POLL_INTERVAL:=10}"

log "Waiting for ${#EXPECTED_NODES[@]} expected node(s) to join and become Ready (up to ${JOIN_TIMEOUT}s)..."
deadline=$(( $(date +%s) + JOIN_TIMEOUT ))
missing=()
while true; do
  ready_now=$(sudo k0s kubectl get nodes --no-headers 2>/dev/null | awk '$2 == "Ready" {print $1}' || true)
  missing=()
  for n in "${EXPECTED_NODES[@]}"; do
    grep -qx "$n" <<<"$ready_now" || missing+=("$n")
  done
  [ "${#missing[@]}" -eq 0 ] && break
  [ "$(date +%s)" -ge "$deadline" ] && break
  sleep "$JOIN_POLL_INTERVAL"
done

if [ "${#missing[@]}" -gt 0 ]; then
  log "⚠️  giving up on ${#missing[@]} node(s) that never joined/became Ready after ${JOIN_TIMEOUT}s, proceeding without them: ${missing[*]}"
  STILL_EXPECTED=()
  for n in "${EXPECTED_NODES[@]}"; do
    grep -qxF "$n" <<<"$(printf '%s\n' "${missing[@]}")" || STILL_EXPECTED+=("$n")
  done
  EXPECTED_NODES=("${STILL_EXPECTED[@]}")
fi
[ "${#EXPECTED_NODES[@]}" -eq 0 ] && fail "no expected nodes ever became Ready -- nothing to distribute images to"
log "Proceeding with ${#EXPECTED_NODES[@]} Ready node(s): ${EXPECTED_NODES[*]}"

################################################################################
# Step 3: build one bundle tar per node role. This k0s release (v1.27.13+k0s.0)
# doesn't have `k0s airgap bundle-artifacts` (that's a newer k0s addition) —
# only `k0s airgap list-images`. So we pull each image into the controller's
# own containerd with `k0s ctr images pull`, then `images export` groups of
# them into per-role tars, exactly what bundle-artifacts would have produced.
################################################################################
# Every Chronos node is amd64 (CloudLab c6620/c6525-25g/d6515 are all x86_64).
PLATFORM="linux/amd64"

log "Pulling images onto the controller..."
UNIQUE_IMAGES=$(printf '%s\n' "$CORE_IMG" "$GLOBALSC_IMG" "$GNB_IMG" "$PROXY_IMG" "$UE_IMG" "$UEDP_IMG" "$MONGO_IMG" "$PERSISTUE_IMG" | sort -u)
while IFS= read -r img; do
  log "  pulling $img"
  sudo k0s ctr --namespace k8s.io images pull --platform "$PLATFORM" "$img" >/dev/null
  # Flatten in place (same source and target ref): a multi-arch image (e.g.
  # the public python:trixie base for persistue) still carries its manifest
  # *index*, referencing every platform's digest, even after a --platform
  # pull only fetched amd64's content. Exporting that index as-is produces a
  # tar that references digests for platforms it never pulled, which then
  # fails to import elsewhere with "content digest ... not found". Converting
  # onto the same tag replaces the index with a single-platform manifest
  # without changing the ref pods actually request.
  sudo k0s ctr --namespace k8s.io images convert --platform "$PLATFORM" "$img" "$img" >/dev/null
done <<<"$UNIQUE_IMAGES"
log "All images pulled ✓"

log "Exporting per-role bundles..."
sudo k0s ctr --namespace k8s.io images export --platform "$PLATFORM" "$WORKDIR/ins.tar" "$GNB_IMG" "$UE_IMG" "$UEDP_IMG"
# Every core pod (scheduled on proxy-* nodes) also runs a mongodb sidecar.
sudo k0s ctr --namespace k8s.io images export --platform "$PLATFORM" "$WORKDIR/proxy.tar" "$CORE_IMG" "$PROXY_IMG" "$MONGO_IMG"
# persistue is pinned to the globalsc node (nodeSelector kubernetes.io/hostname: globalsc).
sudo k0s ctr --namespace k8s.io images export --platform "$PLATFORM" "$WORKDIR/globalsc.tar" "$GLOBALSC_IMG" "$UEDP_IMG" "$PERSISTUE_IMG"
log "Bundles built ✓"

################################################################################
# Step 4: ship bundles out sequentially (so we don't split the controller's
# uplink across concurrent transfers), then import them in parallel (which is
# local CPU/disk work on each remote node and doesn't contend for bandwidth).
################################################################################
node_bundle() {
  case "$1" in
    ins*vm)   echo "$WORKDIR/ins.tar" ;;
    proxy-*)  echo "$WORKDIR/proxy.tar" ;;
    globalsc) echo "$WORKDIR/globalsc.tar" ;;
    *) fail "don't know which bundle node '$1' needs" ;;
  esac
}
export -f node_bundle

# Derived directly from the addressing scheme in profile.py, rather than
# trusting k0s's own "InternalIP" for each node: proxy-*/globalsc nodes are
# outer bare-metal nodes with two interfaces, and k0s reports the public
# CloudLab control-plane IP as InternalIP, not the 10.x experiment-LAN address
# these bundles need to travel over.
node_ip() {
  case "$1" in
    ins*vm)
      local idx="${1#ins}"; idx="${idx%vm}"
      echo "10.2.$((idx + 1)).2"
      ;;
    proxy-*)
      local idx="${1#proxy-}"
      echo "10.3.$((idx + 1)).1"
      ;;
    globalsc)
      echo "10.4.1.1"
      ;;
    *) fail "don't know the address for node '$1'" ;;
  esac
}
export -f node_ip

# ins*vm nodes are uvt-kvm guests (cloud image, real "ubuntu" user, needs
# sudo). proxy-*/globalsc are bare-metal outer nodes with no "ubuntu" account
# at all — the startup scripts trust the shared experiment key for root
# there instead, and root needs no sudo.
node_user() {
  case "$1" in
    ins*vm)            echo "ubuntu" ;;
    proxy-*|globalsc)  echo "root" ;;
    *) fail "don't know the ssh user for node '$1'" ;;
  esac
}
export -f node_user

# ins*vm nodes need sudo for k0s commands (logged in as "ubuntu"); proxy-*/
# globalsc are already root.
remote_prefix() {
  case "$1" in
    ins*vm) echo "sudo " ;;
    *)      echo "" ;;
  esac
}
export -f remote_prefix

# Which images a node's role actually needs -- the same lists used to build
# each bundle above, kept in one place so the "does it already have them"
# check can't drift from what's actually exported into the tar.
node_images() {
  case "$1" in
    ins*vm)   printf '%s\n' "$GNB_IMG" "$UE_IMG" "$UEDP_IMG" ;;
    proxy-*)  printf '%s\n' "$CORE_IMG" "$PROXY_IMG" "$MONGO_IMG" ;;
    globalsc) printf '%s\n' "$GLOBALSC_IMG" "$UEDP_IMG" "$PERSISTUE_IMG" ;;
    *) fail "don't know which images node '$1' needs" ;;
  esac
}
export -f node_images

# Checks the node's *actual* containerd state over SSH rather than trusting
# any local fingerprint of the tar -- ctr's own image list is the only
# guaranteed-correct source of "does this node already have it".
node_has_all_images() {
  local n="$1" ip user prefix present img
  ip=$(node_ip "$n")
  user=$(node_user "$n")
  prefix=$(remote_prefix "$n")
  present=$(ssh $SSH_OPTS "${user}@${ip}" "${prefix}k0s ctr --namespace k8s.io images ls -q" 2>/dev/null) || return 1
  while IFS= read -r img; do
    grep -qxF "$img" <<<"$present" || return 1
  done < <(node_images "$n")
  return 0
}
export -f node_has_all_images

log "Copying bundles to nodes that need them (sequential)..."
TO_IMPORT=()
for n in "${EXPECTED_NODES[@]}"; do
  if node_has_all_images "$n"; then
    log "  -> $n: already has all expected images, skipping"
    continue
  fi
  ip=$(node_ip "$n")
  user=$(node_user "$n")
  bundle=$(node_bundle "$n")
  log "  -> $n (${user}@${ip}): $(basename "$bundle")"
  scp $SSH_OPTS "$bundle" "${user}@${ip}:/var/tmp/images.tar"
  TO_IMPORT+=("$n")
done
log "Bundle copy phase done ✓"

import_on() {
  local n="$1" ip user prefix
  ip=$(node_ip "$n")
  user=$(node_user "$n")
  prefix=$(remote_prefix "$n")
  ssh $SSH_OPTS "${user}@${ip}" "${prefix}k0s ctr --namespace k8s.io images import /var/tmp/images.tar"
}
export -f import_on
export SSH_OPTS

if [ "${#TO_IMPORT[@]}" -gt 0 ]; then
  log "Importing images on ${#TO_IMPORT[@]} node(s) (parallel)..."
  printf '%s\n' "${TO_IMPORT[@]}" | parallel --will-cite import_on {}
else
  log "Every node already had its images -- nothing to import."
fi
log "✅ download_images.sh complete: ${#TO_IMPORT[@]}/${#EXPECTED_NODES[@]} node(s) updated"
