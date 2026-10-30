# Lean4 + Mathlib Offline Build (github.com blocked)

Recipe for compiling a standalone `.lean` project that does `import Mathlib`
when `github.com:443` is unreachable but `codeload.github.com` (the git-archive
CDN) IS reachable. Validated 2026-08-15 on the V63 neutrino paper
(`Neutrino_Condensation_proof_63.lean`, Lean 4.34.0-rc1 / Lake 5.0.0).

## The core problem

Lake resolves `require ... @ git` by (a) reading each dependency's
`lake-manifest.json` for its URL + rev, then (b) running `git` against the
package directory to verify the rev matches. A zip-extracted package is NOT a
git repo, so Lake fails with `fatal: not a git repository` / `URL has changed;
you might need to delete ... manually` and then tries (and fails) to `git clone`
from github.com.

Fix: make the ROOT project lakefile require every dependency by LOCAL PATH,
which overrides the transitive git `require`s.

## Steps

### 1. Get mathlib + its dependency revs

The dependency list is authoritative in **mathlib's own `lake-manifest.json`**
(the `packages` array: `url`, `rev`, `name`, `inputRev`, `inherited`). mathlib
directly requires 7 packages + 1 inherited (`Cli` = lean4-cli):

| Lake name  | Actual GitHub repo (org=leanprover-community unless noted) | branch |
|-----------|-------------------------------------------------------------|--------|
| batteries | batteries | main |
| Qq        | **quote4** (repo ≠ name) | master |
| aesop     | aesop | master |
| proofwidgets | **ProofWidgets4** (repo ≠ name) | main |
| importGraph | **import-graph** (repo ≠ name) | main |
| LeanSearchClient | LeanSearchClient | main |
| plausible | plausible | main |
| Cli       | leanprover/**lean4-cli** (inherited, org=leanprover) | v4.34.0-rc1 |

### 2. Download each package as a zip by exact rev

```bash
# github.com git clone is blocked; codeload CDN works:
curl -sL -o <LakeName>.zip \
  "https://codeload.github.com/<org>/<repo>/zip/<rev>"
```

The zip's top-level directory is `<repo>-<rev>`; extract and RENAME to the
**Lake name** (not the repo name):

```python
import zipfile, os, shutil
with zipfile.ZipFile(z) as zf:
    top = zf.namelist()[0].split('/')[0]; zf.extractall(base)
os.rename(os.path.join(base, top), os.path.join(base, lake_name))
```

Place under `<root>/.lake/packages/<LakeName>/`.

### 3. Root lakefile: local-path require + explicit roots

```lean
import Lake
open Lake DSL

package «neutrino» where
@[default_target]
lean_lib «Neutrino» where
  roots := #[`Neutrino_Condensation_proof_63]   -- actual root module, NOT the lib name

require batteries from ".lake/packages/batteries"
require Qq from ".lake/packages/Qq"
require aesop from ".lake/packages/aesop"
require proofwidgets from ".lake/packages/proofwidgets"
require importGraph from ".lake/packages/importGraph"
require LeanSearchClient from ".lake/packages/LeanSearchClient"
require plausible from ".lake/packages/plausible"
require Cli from ".lake/packages/Cli"
require mathlib from "../<path>/mathlib"
```

Two independent gotchas solved here:

- **`roots := #[`ActualModule]`** — the default root module name is the
  `lean_lib` name (`Neutrino`), so Lake looks for `Neutrino.lean` and dies with
  `no such file or directory ... Neutrino.lean` / `some modules have bad
  imports`. Point `roots` at the real filename (without `.lean`).
- **local-path `require` for every transitive dep** — overrides mathlib's git
  requires so Lake never invokes git.

### 4. Build without the precompiled-olean cache

mathlib's `post_update` hook runs `lake exe cache get` (downloads prebuilt
`.olean`). Skip it:

```bash
MATHLIB_NO_CACHE_ON_UPDATE=1 lake build
```

Full source compile of mathlib is ~8725 modules, roughly 2-3 hours (as of
2026-08). Use `terminal(background=true, notify_on_complete=true)`.

## Verification order

The build compiles dependencies first (batteries/aesop/proofwidgets ~ 400
modules), then the Mathlib core, then your project. A syntax error in YOUR
file only surfaces at the very end — so sanity-check any newly added
`structure`/`theorem` blocks statically (arities, field access) before
committing to a multi-hour build.

## Not a durable rule

The github.com block is environment-specific; codeload reachability may change.
The durable lesson is the *mechanism*: local-path `require` in the root
lakefile overrides transitive git requires, and `roots` must name the actual
root module file. Re-verify network reachability each time rather than assuming
github.com is down.
