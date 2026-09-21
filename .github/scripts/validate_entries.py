#!/usr/bin/env python3
"""Validate registry entries and reproduce their creation bytecode."""
import glob
import json
import os
import re
import subprocess
import sys
from jsonschema import Draft7Validator

errors = []

with open("schema/entry.schema.json") as schema_file:
    SCHEMA = json.load(schema_file)
SCHEMA_VALIDATOR = Draft7Validator(SCHEMA)


def strip_metadata(bc: str) -> str:
    """Drop the trailing Solidity CBOR metadata (…a264 'ipfs'… or a164 'bzzr'…) for comparison."""
    h = bc[2:] if bc.startswith("0x") else bc
    # metadata length is the last 2 bytes; chop it + the metadata blob if the marker is present.
    m = re.search(r"(a264697066|a164627a7a)", h)
    return h[: m.start()] if m else h


def select_solc(version: str, path: str) -> bool:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append(f"{path}: invalid solc version '{version}'")
        return False

    for command in (["solc-select", "install", version], ["solc-select", "use", version]):
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            errors.append(
                f"{path}: failed to select solc {version}: "
                f"{(result.stderr or result.stdout).strip()[:500]}"
            )
            return False

    installed = subprocess.run(["solc", "--version"], capture_output=True, text=True)
    if installed.returncode != 0 or f"Version: {version}" not in installed.stdout:
        errors.append(f"{path}: solc {version} was not activated")
        return False
    return True


def check(path: str):
    initial_error_count = len(errors)
    try:
        with open(path) as entry_file:
            e = json.load(entry_file)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return

    schema_errors = sorted(SCHEMA_VALIDATOR.iter_errors(e), key=lambda err: list(err.path))
    for error in schema_errors:
        location = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{path}: schema {location}: {error.message}")
    if schema_errors:
        return

    if os.path.basename(path) != f"{e['name']}.json":
        errors.append(f"{path}: filename must match entry name '{e['name']}.json'")

    bc = e["creationBytecode"]
    if not re.fullmatch(r"0x[0-9a-fA-F]+", bc) or len(bc) <= 2:
        errors.append(f"{path}: creationBytecode must be non-empty hex")
    if "__$" in bc:
        errors.append(f"{path}: creationBytecode has unlinked library placeholders")
    if not e["source"].strip():
        errors.append(f"{path}: empty source (inline the flattened source)")
    if len(errors) > initial_error_count:
        return

    if not select_solc(e["solc"], path):
        return

    settings = dict(e["compilerSettings"])
    settings["outputSelection"] = {"*": {"*": ["evm.bytecode.object"]}}
    compiler_input = {
        "language": "Solidity",
        "sources": {"Entry.sol": {"content": e["source"]}},
        "settings": settings,
    }
    out = subprocess.run(
        ["solc", "--standard-json"],
        input=json.dumps(compiler_input),
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        errors.append(f"{path}: source failed to recompile:\n{out.stderr.strip()[:500]}")
        return

    try:
        compiler_output = json.loads(out.stdout)
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: solc returned invalid JSON: {exc}")
        return
    compiler_errors = [
        item.get("formattedMessage", item.get("message", "unknown compiler error"))
        for item in compiler_output.get("errors", [])
        if item.get("severity") == "error"
    ]
    if compiler_errors:
        errors.append(f"{path}: source failed to recompile:\n{compiler_errors[0][:500]}")
        return

    got = (
        compiler_output.get("contracts", {})
        .get("Entry.sol", {})
        .get(e["name"], {})
        .get("evm", {})
        .get("bytecode", {})
        .get("object", "")
    )
    if strip_metadata(got) != strip_metadata(bc):
        errors.append(f"{path}: bytecode != recompile(source, solc, compilerSettings)")
    else:
        print(f"✓ {path}: schema-valid and reproducible")


def main():
    entries = sorted(glob.glob("entries/*.json"))
    if not entries:
        print("no entries to validate")
        return
    for p in entries:
        check(p)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)
    print(f"validated {len(entries)} entr{'y' if len(entries)==1 else 'ies'}")


if __name__ == "__main__":
    main()
