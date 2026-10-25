#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY="https://github.com/andrewferguson/openairinterface-nfapi-netsys.git"
BRANCH="phobos-tdd-ue-real"
SOURCE="${1:-}"
IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-chronos-ue}"
BUILD_JOBS="${BUILD_JOBS:-4}"
SOURCE_DIRTY=false
TAG_SUFFIX=""

if docker info >/dev/null 2>&1; then
    DOCKER=(docker)
elif command -v sudo >/dev/null 2>&1 && sudo -n docker info >/dev/null 2>&1; then
    DOCKER=(sudo -E docker)
else
    echo "ERROR: Docker is unavailable or requires interactive authentication" >&2
    exit 1
fi

if [[ -n "$SOURCE" ]]; then
    [[ -d "$SOURCE" ]] || {
        echo "ERROR: Source directory does not exist: $SOURCE" >&2
        exit 1
    }
    SOURCE="$(cd "$SOURCE" && pwd)"
    [[ "$(git -C "$SOURCE" branch --show-current)" == "$BRANCH" ]] || {
        echo "ERROR: Expected branch $BRANCH in $SOURCE" >&2
        exit 1
    }
    if [[ -n "$(git -C "$SOURCE" status --short)" ]]; then
        SOURCE_DIRTY=true
        TREE_STATE_HASH="$(
            {
                git -C "$SOURCE" diff --binary HEAD
                while IFS= read -r -d '' file; do
                    printf 'untracked:%s\0' "$file"
                    cat "$SOURCE/$file"
                done < <(git -C "$SOURCE" ls-files --others --exclude-standard -z | sort -z)
            } | sha256sum | cut -c1-8
        )"
        TAG_SUFFIX="-dirty-${TREE_STATE_HASH}"
        echo "Source tree is dirty; using content-qualified tag suffix: $TAG_SUFFIX"
    fi
    COMMIT="$(git -C "$SOURCE" rev-parse HEAD)"
    OAI_CONTEXT="$SOURCE"
    echo "Using local OAI source: $SOURCE"
else
    COMMIT="$(git ls-remote "$REPOSITORY" "refs/heads/$BRANCH" | awk '{print $1}')"
    [[ -n "$COMMIT" ]] || {
        echo "ERROR: Could not resolve $BRANCH from $REPOSITORY" >&2
        exit 1
    }
    OAI_CONTEXT="${REPOSITORY}#${BRANCH}"
    echo "No source directory supplied; using $OAI_CONTEXT"
fi

TAG="${COMMIT:0:8}${TAG_SUFFIX}"
IMAGE="${IMAGE:-${IMAGE_REPOSITORY}:${TAG}}"

if [[ "${RESOLVE_ONLY:-0}" == "1" ]]; then
    echo "Resolved image: $IMAGE"
    exit 0
fi

args=(
    build
    --load
    --file "$SCRIPT_DIR/Dockerfile.ue"
    --build-context "oai-source=$OAI_CONTEXT"
    --build-arg "BUILD_JOBS=$BUILD_JOBS"
    --build-arg "SOURCE_COMMIT=$COMMIT"
    --build-arg "SOURCE_DIRTY=$SOURCE_DIRTY"
    --tag "$IMAGE"
)

if [[ -n "${PUSH:-}" ]]; then
    echo "ERROR: build.sh only builds and loads images locally" >&2
    exit 2
fi

args+=("$SCRIPT_DIR")

echo "Building $IMAGE from $COMMIT"
"${DOCKER[@]}" buildx "${args[@]}"
