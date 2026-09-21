# Contributing an entry

An entry is **one self-contained contract** — most often a **behavioral integration mock** (a
"puzzle piece" that makes a third-party protocol behave naturally so a dependent project can be
fuzzed against it), or a standalone mock/tester. One contract, one JSON, one deploy.

> See `skills/registry-integration/` for the full 0→100 guide (what to model, what to mock, the
> per-class behaviors catalog, and how a piece plugs into an operator suite).

## 1. Scaffold (in your Foundry project)
```
npx recon-registry init
```
Creates `recon-registry.toml` and `registry/{Harness.sol,Rvm.sol,IERC20.sol,README.md}` (idempotent).

## 2. Write the piece
Edit `registry/Harness.sol` (rename the contract). A **behavioral integration mock**:
- Models **only the surface the dependent project touches**; mocks/stubs/omits the rest.
- Is **faithful on the dynamics that affect dependents** (rates, price impact, rounding, liquidation,
  accrual) — not the integration's full internals.
- Has **actor handlers** (`external ... asActor`) for the natural churn that perturbs dependents.
- `constructor() asAdmin` deploys the touched surface, **`rvm.register`s entry points by label**, and
  funds/approves `rvm.getActors()`. `new`'d deps are embedded → single self-contained artifact.
- Deps are **`Rvm` + `IERC20` only**; `asActor`/`asAdmin` are inlined (no BaseTargets/ghosts/properties
  — a piece does not test the integration's invariants).

Fill in `recon-registry.toml` (`name`, `description`, `tags`, `harness`, the `labels` you register, `solc`).

Rules:
- **Single contract.** No external deployed-library linking left unresolved (link libs, or use
  internal libraries). `pack` rejects unlinked bytecode (`__$` placeholders).
- **No constructor args** (pull actors via `rvm`; deploy/wire in the constructor).
- **Declare your labels** so a SUT suite can resolve your entry points via `rvm.getAddr("...")`.
- Keep `[build].skip` set so clashing basenames (e.g. multiple `MockERC20.sol`) don't clobber the
  artifact.

## 3. Pack
```
npx recon-registry pack
```
Runs `forge build`, extracts the concrete artifact (asserts non-empty, linked bytecode), inlines
the source, stamps `solc`, and writes `recon-registry-out/<name>.json`.

## 4. Publish
```
npx recon-registry publish
```
Submits the entry to the registry's Action, which validates it and opens a PR. **No `gh`/fork needed:** with a `GH_TOKEN`/`GITHUB_TOKEN` it fires a `repository_dispatch`; otherwise it opens a prefilled issue in your browser and reveals the entry file to drag in.

## CI gate
Your PR must pass: **bytecode == recompile(source, solc)** (reproducibility), schema validation,
and a smoke deploy. On merge, `registry.json` is rebuilt and your entry is live for everyone.

## Schema
See `schema/entry.schema.json`. Entries: `name, description, tags, abi, creationBytecode, source,
solc, compilerSettings`. The packer reads compiler settings from the Forge artifact; trust comes
from the CI reproducibility check.
