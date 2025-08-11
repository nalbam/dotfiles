#!/bin/bash
# Read JSON input from stdin
input=$(cat)

# Extract values using jq
MODEL_DISPLAY=$(echo "$input" | jq -r '.model.display_name')
CURRENT_DIR=$(echo "$input" | jq -r '.workspace.current_dir')
PROJECT_DIR=$(echo "$input" | jq -r '.workspace.project_dir')

# Get directory name
DIR_NAME=$(basename "$CURRENT_DIR")

# Check if we're in a git repository and get branch info
GIT_INFO=""
if [ -d "$CURRENT_DIR/.git" ] || git -C "$CURRENT_DIR" rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git -C "$CURRENT_DIR" branch --show-current 2>/dev/null)
    if [ -n "$BRANCH" ]; then
        # Check for uncommitted changes
        if ! git -C "$CURRENT_DIR" diff-index --quiet HEAD -- 2>/dev/null; then
            GIT_INFO=" git:($BRANCH ✗)"
        else
            GIT_INFO=" git:($BRANCH)"
        fi
    fi
fi

# Get Kubernetes context if kubectl is available
KUBE_INFO=""
if command -v kubectl > /dev/null 2>&1; then
    KUBE_CONTEXT=$(kubectl config current-context 2>/dev/null)
    if [ -n "$KUBE_CONTEXT" ]; then
        KUBE_NAMESPACE=$(kubectl config view --minify --output 'jsonpath={..namespace}' 2>/dev/null)
        if [ -n "$KUBE_NAMESPACE" ] && [ "$KUBE_NAMESPACE" != "default" ]; then
            KUBE_INFO="⎈ ($KUBE_CONTEXT:$KUBE_NAMESPACE) "
        else
            KUBE_INFO="⎈ ($KUBE_CONTEXT) "
        fi
    fi
fi

# Build the status line in the style of your Dracula zsh theme
printf "%s➜  %s%s [%s]" "$KUBE_INFO" "$DIR_NAME" "$GIT_INFO" "$MODEL_DISPLAY"
