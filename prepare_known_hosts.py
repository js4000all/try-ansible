#!/usr/bin/env python3
"""Register SSH host keys for both current and planned inventory IPs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def run(command, *, input=None, check=True):
    return subprocess.run(command, input=input, text=True, capture_output=True, check=check)


def host_label(address, port):
    return address if port == 22 else f"[{address}]:{port}"


def existing_keys(path, label):
    if not path.exists():
        return {}
    result = run(["ssh-keygen", "-F", label, "-f", str(path)], check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or f"ssh-keygen -F failed for {label}")
    keys = {}
    for line in result.stdout.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        fields = line.split()
        if len(fields) >= 3:
            keys.setdefault(fields[1], set()).add(fields[2])
    return keys



def trusted_keys(path):
    """Return host public keys already present anywhere in known_hosts."""
    trusted = set()
    if not path.exists():
        return trusted
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        # Marker entries (@cert-authority, @revoked) must not establish trust.
        if fields[0].startswith("@"):
            continue
        if len(fields) >= 3 and fields[1].startswith(("ssh-", "ecdsa-", "sk-")):
            trusted.add((fields[1], fields[2]))
    return trusted


def fingerprint(key_type, key):
    result = run(["ssh-keygen", "-lf", "-", "-E", "sha256"],
                 input=f"{key_type} {key}\n")
    return result.stdout.strip()


def confirm_new_keys(new_keys, sources):
    if not new_keys:
        return
    if not sys.stdin.isatty():
        raise RuntimeError("New host keys require interactive confirmation (TTY)")
    print("\nNew SSH host keys not found anywhere in known_hosts:")
    print("Verify these fingerprints using a trusted channel before accepting.")
    for key_type, key in sorted(new_keys):
        print(f"\n  Hosts: {', '.join(sorted(sources[(key_type, key)]))}")
        print(f"  {fingerprint(key_type, key)}")
        response = input("  Trust this key? [y/N]: ").strip().lower()
        if response not in ("y", "yes"):
            raise RuntimeError("Confirmation declined; known_hosts was not modified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--inventory", default="hosts.yml")
    parser.add_argument("-f", "--known-hosts", type=Path, default=Path.home() / ".ssh/known_hosts")
    args = parser.parse_args()
    path = args.known_hosts.expanduser()

    inventory = json.loads(run(["ansible-inventory", "-i", args.inventory, "--list"]).stdout)
    hostvars = inventory.get("_meta", {}).get("hostvars", {})
    if not hostvars:
        raise RuntimeError("No hosts found in inventory")

    # Collect keys first; do not touch known_hosts until every scan is successful.
    wanted = {}  # label -> {key_type: base64_key}
    sources = {}  # (key_type, base64_key) -> host names
    for name, variables in sorted(hostvars.items()):
        current = variables.get("ansible_host", name)
        future = variables.get("network_ipv4_address")
        if not future:
            print(f"SKIP {name}: network_ipv4_address is unset", file=sys.stderr)
            continue
        port = int(variables.get("ansible_port", 22))
        scan = run(["ssh-keyscan", "-T", "5", "-p", str(port), "-t", "ed25519,ecdsa,rsa", str(current)], check=False)
        found = {}
        for line in scan.stdout.splitlines():
            fields = line.split()
            if len(fields) >= 3 and not line.startswith("#"):
                found[fields[1]] = fields[2]
        if not found:
            raise RuntimeError(f"{name} ({current}): ssh-keyscan returned no host keys: {scan.stderr.strip()}")
        for key_type, key in found.items():
            sources.setdefault((key_type, key), set()).add(f"{name} ({current} -> {future})")
        for address in {str(current), str(future)}:
            label = host_label(address, port)
            target = wanted.setdefault(label, {})
            for key_type, key in found.items():
                if key_type in target and target[key_type] != key:
                    raise RuntimeError(f"Conflicting scanned keys for {label} ({key_type})")
                target[key_type] = key
        print(f"SCAN {name}: {current} -> {future} ({len(found)} key types)")

    additions = []
    trusted = trusted_keys(path)
    untrusted = set()
    for label, keys in sorted(wanted.items()):
        old = existing_keys(path, label)
        for key_type, key in sorted(keys.items()):
            if key_type in old and old[key_type] != {key}:
                raise RuntimeError(f"Host key mismatch for {label} ({key_type}); known_hosts was not modified")
            if key_type not in old:
                additions.append(f"{label} {key_type} {key}\n")
                if (key_type, key) not in trusted:
                    untrusted.add((key_type, key))

    # Confirm every genuinely new public key before touching the file.
    confirm_new_keys(untrusted, sources)

    if additions:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a") as output:
            output.writelines(additions)
    print(f"DONE: added {len(additions)} entries to {path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError, RuntimeError) as error:
        sys.exit(f"ERROR: {error}")
