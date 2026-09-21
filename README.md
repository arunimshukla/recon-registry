# recon-registry

A community catalog of **single self-contained fuzzing harnesses and mocks**, deployable **by
name** into the [Recon operator](https://github.com/Recon-Fuzz/recon-fuzzer). Package a whole
protocol (or a standalone tester like an ERC-4626 vault or a weird ERC-20) into **one
self-contained contract** whose constructor stands the project up — then anyone can fuzz it.

```
operator (Rust)                 recon-registry (this repo)              you (a Foundry project)
  deploy_from_registry(name) ──▶  entries/<name>.json  ◀── PR ──  npx recon-registry pack/publish
```

## Use an entry (consumer)
From the operator: `deploy_from_registry("ERC4626Tester", as_actor: true)` — fetches the entry
and stands the project up at a deterministic address. Browse: `npx recon-registry list`.

## Contribute an entry (author)
In your Foundry project:
```
npx recon-registry init       # scaffold recon-registry.toml + registry/Harness.sol + Rvm.sol
# write your harness (its constructor news+wires the whole project; see registry/Harness.sol)
npx recon-registry pack       # forge build + extract → recon-registry-out/<name>.json
npx recon-registry publish    # write token → auto-PR; else opens a prefilled issue (one Ctrl+V)
```

## Model (intentionally simple)
- **One entry = one contract.** A "project" is a single self-contained Setup-style harness whose
  creation bytecode embeds and deploys its deps. No multi-contract manifests, no dependency
  ordering.
- **Entry schema** (`schema/entry.schema.json`): `name, description, tags, abi, creationBytecode,
  source, solc, compilerSettings`. Source is inlined (humans + the LLM read behavior); compiler
  version and code-generation settings are pinned so CI can reproduce the bytecode.
- **Formats:** manifest = TOML (`recon-registry.toml`, human-edited); entries = JSON
  (`entries/*.json`, machine-generated). Same split as `foundry.toml` ↔ `out/*.json`.

## Trust = reproducibility, enforced in CI
On every PR, CI recompiles the entry's `source` with its `solc` and asserts the **bytecode
matches**, validates the schema, and smoke-deploys. On merge to `main`, `registry.json` is
rebuilt and the entry is immediately available to the operator (merge = publish).

## Layout
```
entries/*.json   published entries (machine-generated)
src/*.sol        the harness/mock sources (for browsing + CI recompile)
schema/          the entry JSON schema
registry.json    the catalog index (CI-generated on merge)
```

See `CONTRIBUTING.md` for the full author guide.
