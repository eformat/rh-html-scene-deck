#!/usr/bin/env bash
# deploy.sh — render templates with envsubst, build with kustomize, apply.
#
# Usage:
#   ./deploy.sh                # uses env.local next to this script
#   ./deploy.sh path/to/env-file
#
# Pipeline: envsubst templates → build/ → kubectl apply -k build/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${1:-$SCRIPT_DIR/env.local}"

if [ ! -f "$ENV_FILE" ]; then
    echo "no env file at $ENV_FILE"
    echo "copy env.example to env.local, edit it, and re-run"
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${APP_NAME:?set APP_NAME in $ENV_FILE}"
: "${NAMESPACE:?set NAMESPACE in $ENV_FILE}"
: "${CONFIGMAP_NAME:?set CONFIGMAP_NAME in $ENV_FILE}"
: "${DECK_FILE:?set DECK_FILE in $ENV_FILE}"
[ -f "$DECK_FILE" ] || { echo "deck not found: $DECK_FILE"; exit 1; }

BUILD="$SCRIPT_DIR/build"
rm -rf "$BUILD"
mkdir -p "$BUILD"

# envsubst only the variables the templates reference — never the whole env
export APP_NAME NAMESPACE CONFIGMAP_NAME
envsubst '$APP_NAME $NAMESPACE $CONFIGMAP_NAME' \
    < "$SCRIPT_DIR/deployment.template.yaml"   > "$BUILD/deployment.yaml"
envsubst '$APP_NAME $NAMESPACE $CONFIGMAP_NAME' \
    < "$SCRIPT_DIR/kustomization.template.yaml" > "$BUILD/kustomization.yaml"

cp "$DECK_FILE" "$BUILD/index.html"

kubectl apply -k "$BUILD"
kubectl -n "$NAMESPACE" rollout status "deployment/$APP_NAME" --timeout=120s

echo
echo "deck deployed — app=$APP_NAME namespace=$NAMESPACE"
echo "  view it:"
echo "    kubectl -n $NAMESPACE port-forward deploy/$APP_NAME 8080:8080"
echo "    then open http://localhost:8080"
