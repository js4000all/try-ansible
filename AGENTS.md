# Agent instructions

This repository manages machines with Ansible. Keep changes small, reviewable, and consistent with existing roles and playbooks.

## Before editing

- Inspect the relevant playbooks, roles, inventory variables, and existing conventions before changing code.
- Prefer Ansible built-in modules and idempotent tasks over shell commands. When a command is necessary, define how changes are detected.
- Keep functionality in focused `roles/<role>/`; attach roles to the appropriate `playbooks/*.yml` and follow existing role-tag conventions.
- Preserve the distinction between controller-side operations and target-side operations. Pay attention to `become`, `become: false`, `ansible_user`, and which user's home directory is modified.
- Do not commit secrets, SSH private keys, authentication tokens, or local inventory credentials. Inspect `.gitignore` and use the existing inventory/group_vars conventions.

## Required validation

- Run `./lint.sh` after changing Ansible, YAML, or supporting scripts, and before reporting the work as complete.
- This script runs `yamllint`, `ansible-lint`, and playbook syntax checks using the repository's Docker-based execution environment.
- If the checks cannot run (for example, Docker, `.env`, or dependencies are missing), report that explicitly. Never claim validation succeeded without running it.
- Address relevant failures caused by your changes. Distinguish pre-existing failures from new ones, and report any remaining failures.
- Review the diff for unintended changes and sensitive information.

## Operations and safety

- Static validation does not authorize applying a playbook to live hosts.
- Do not run `ansible-playbook` against real targets, bootstrap machines, change networking, repartition disks, or otherwise modify remote systems unless explicitly requested.
- If a live run is requested, use the narrowest practical host limit and tags, and check the intended inventory and target first.
- Avoid changing unrelated files or introducing new dependencies without a clear need.

## Communication

- Summarize what changed and why, what validation actually ran and its result, and any unverified assumptions or operational risks.
- Do not describe an installation, remote test, or configuration as verified unless it was actually performed.
