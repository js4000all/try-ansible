#!/bin/sh
set -eu

ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo "env file not found: $ENV_FILE" >&2
    exit 1
fi

# 単純な KEY=VALUE だけを置く前提
set -a
. "$ENV_FILE"
set +a

if [ -z "${SSH_KEY_PATH:-}" ]; then
    echo "SSH_KEY_PATH is not set" >&2
    exit 1
fi

if [ ! -f "$SSH_KEY_PATH" ]; then
    echo "SSH key not found: $SSH_KEY_PATH" >&2
    exit 1
fi

case "${1:-}" in
    adhoc)
        shift
        ANSIBLE_CMD=ansible
        ;;
    *)
        ANSIBLE_CMD=ansible-playbook
        ;;
esac


cleanup() {
    ssh-agent -k >/dev/null 2>&1 || true
}

eval "$(ssh-agent -s)" >/dev/null
trap cleanup EXIT INT TERM

ssh-add "$SSH_KEY_PATH"
docker compose run --rm ops $ANSIBLE_CMD -i "$INVENTORY" "$@"
