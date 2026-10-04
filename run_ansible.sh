#!/bin/sh
set -eu

# スクリプト自身が置かれているディレクトリを基準にする
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

ENV_FILE="$SCRIPT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "env file not found: $ENV_FILE" >&2
    exit 1
fi

# 信頼できる単純な KEY=VALUE のみを置く前提
set -a
. "$ENV_FILE"
set +a

: "${SSH_KEY_PATH:?SSH_KEY_PATH is not set}"
: "${INVENTORY:?INVENTORY is not set}"

if [ ! -f "$SSH_KEY_PATH" ]; then
    echo "SSH key not found: $SSH_KEY_PATH" >&2
    exit 1
fi

if ! command -v ssh-agent >/dev/null 2>&1; then
    echo "ssh-agent command not found" >&2
    exit 1
fi

if ! command -v ssh-add >/dev/null 2>&1; then
    echo "ssh-add command not found" >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "docker command not found" >&2
    exit 1
fi

case "${1:-}" in
    adhoc)
        ANSIBLE_CMD="ansible"
        shift
        ;;
    *)
        ANSIBLE_CMD="ansible-playbook"
        ;;
esac

cleanup() {
    ssh-agent -k >/dev/null 2>&1 || true
}

eval "$(ssh-agent -s)" >/dev/null
trap cleanup EXIT HUP INT TERM

ssh-add "$SSH_KEY_PATH"

docker compose run --rm \
    -f compose.yml \
    -f compose.ssh.yml \
    -w /work \
    ops \
    "$ANSIBLE_CMD" -i "$INVENTORY" "$@"
