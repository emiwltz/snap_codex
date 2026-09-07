# Local reproduction

This guide uses the environment installed in the [README](../README.md). Python
3.12 and `paper/requirements.lock.txt` are the verified combination. Installation
may use the network; all analysis below is offline and needs no provider key.

## 1. Check code locally

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.runner --help
```

The test fixture blocks socket `connect`, `connect_ex` and `create_connection`.
Tests use temporary databases and mock provider transports. The network guard is
an accident-prevention measure inside Python, not an operating-system sandbox.

## 2. Recompute evidence in a new directory

```bash
.venv/bin/python scripts/reproduce.py --output-dir artifacts/runs/review-01
```

Choose a new run name each time. Existing destinations, reference directories and
symlink paths resolving outside the permitted output trees are refused. The
script checks required inputs before creating its output. A presentation export
omits raw inputs and therefore reports them as unavailable; see [DATA](DATA.md).

The pipeline performs consistent SQLite backups through `Connection.backup`
from URI `mode=ro` connections, copies the configuration and only opens those
backups with `SoulBenchDB`. It does not issue a provider completion, regenerate
scores, resolve a pending human decision or change reference files.

Expected outputs include:

- `audit.json`: completeness, schedule, prompt and data correspondence checks,
  before/after input hashes, package versions and archived-report differences.
- `core/decision_report.json`: readiness **complete**, scientific decision **FAIL**.
- CSV tables and `figures/`: aggregate statistics, uncertainty and diagnostics.
- `metrics.json`: nominal and ordinal agreement with explicit populations,
  truncation and exploratory sensitivity results.

Check every audit boolean and the empty comparison lists, not only exit code 0.
The comparison covers stability, sensitivity, variance and decision with absolute
and relative tolerance 10⁻⁸, ignoring only `generated_at`. Five complete ICCs are
also checked using an independent ANOVA calculation. Unverified human provenance,
missing Claude coverage and absent backend revisions are recorded as limitations,
not hidden as passed checks.

Bootstrap diagnostics use 5,000 replicates and seed 20260904. They may take a few
minutes. Numeric results are compared with tolerance rather than promising binary
identity across library, font or operating-system versions.

## 3. Rebuild a review copy of the manuscript

Edit `paper/manuscript.template.md`, not the rendered Markdown. Reproduce the
evidence first so the builder can verify input hashes against the current code.

```bash
.venv/bin/python paper/scripts/build_manuscript.py --results-dir artifacts/runs/review-01 --output-dir paper/build/review-01
```

This writes a separate manuscript, bibliography, supplement, results copy and PDF
under `paper/build/review-01/`. It refuses an existing destination and leaves the
reading copy and retained aggregates in `paper/` intact. A stale input hash or
failed audit prevents rendering. Both the source snapshots and the rendered
results must be reviewed together; the builder does not choose a favourable run.

For visual review, install Poppler separately if `pdftoppm` is unavailable:

```bash
mkdir -p paper/build/review-01/qa/pages
pdftoppm -r 110 -png paper/build/review-01/output/pdf/snap_v3_1_manuscript.pdf paper/build/review-01/qa/pages/page
```

Inspect every page after substantive edits. Text extraction cannot establish that
figures, tables, references and page boundaries remain readable. Promotion of a
review copy to the reading manuscript is a separate, reviewable file change.

## Lower-level commands and their effects

| Command | Effect |
|---|---|
| `python -m src.runner --help` | Describes CLI options; does not open a database |
| `analyze`, `visualize`, `decision` | Read analyses but open through `SoulBenchDB`, which initializes/migrates; use a copy |
| `compute-kappa` | Writes derived results; use a separate validation backup |
| `init-db`, `import-manual`, `adjudicate` | Write to the selected database |
| `preflight` | Queries the public model catalogue; not offline and not proof of authentication/completion availability |
| `collect`, `score` | Can send data and incur provider charges; outside this reproduction workflow |

For bespoke local work, create a consistent backup before invoking a lower-level
command. Example from the root, using a new disposable directory:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
import sqlite3
import shutil
run = Path('artifacts/runs/custom-01')
run.mkdir(parents=True, exist_ok=False)
source = Path('data/snap_poc_v3_1.db').resolve()
with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src:
    with sqlite3.connect(run / 'working.db') as dst:
        src.backup(dst)
shutil.copytree('config', run / 'config')
PY
.venv/bin/python -m src.runner --db-path artifacts/runs/custom-01/working.db --config-dir artifacts/runs/custom-01/config analyze --stability --output-dir artifacts/runs/custom-01/reports
```

Keep decision reports and analyses tied to the same DB/config snapshot; the bare
CLI does not enforce their provenance. A public catalogue lookup is distinct from
paid collection. No new campaign is needed to reproduce this study.

`scripts/reproduce_article_artifacts.sh` is now a compatibility wrapper around the
single reproduction entry point. Its previous `cp` recipe remains recoverable in
Git. `scripts/reproduce_preliminary.py` is retained for its statistical helpers and
historical snapshot provenance; its older standalone output is not the current
manuscript evidence path.
