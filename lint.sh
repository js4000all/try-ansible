#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

echo "==> yamllint"
./run_ansible.sh exec yamllint .

echo "==> ansible-lint"
./run_ansible.sh exec ansible-lint .

echo "==> Ansible syntax check"
for playbook in playbook/*.yml; do
    [ -f "$playbook" ] || continue

    echo "Checking: $playbook"
    ./run_ansible.sh --syntax-check "$playbook"
done

echo "==> All checks passed"
