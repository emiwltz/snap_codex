# SoulBench SNAP

**Response profiles under controlled prompting. A reproducible preliminary study with a negative protocol result.**

SNAP measures how language models respond to ambiguous situations when system
framing, scenario wording and selected inference settings vary. It studies coded
outputs; it does **not** establish intrinsic personality, values or psychology.

The retained v3.1 campaign contains **2,700 responses from six model endpoints**,
15 items, three system conditions and ten scheduled runs per cell. The pipeline
completed collection, scoring and analysis. The historical readiness gate was
met, but the scientific decision is **FAIL**: stability and context-robustness
criteria were not all satisfied. No thresholds were relaxed to obtain a better
result.

## Read the study

- [Manuscript and reading guide](paper/README.md): English working preprint, PDF,
  methods, results, discussion and reproducible figures.
- [French synthesis](paper/SYNTHESE_FR.md): findings and practical limits.
- [Claims and evidence](paper/CLAIMS.md): which conclusions are supported, by what,
  and with which limitations.
- [Next experiments](paper/EXPERIMENT_PLAN.md): prioritized work, distinct from
  the completed reference campaign.

| Historical check | Verified value | Interpretation |
|---|---:|---|
| Inter-judge agreement | κ = 0.7509 | 2,695 complete judge pairs; five second-judge scores missing |
| Refusal rate | 2/2,700 = 0.074% | 2,698 responses enter numerical analyses |
| Minimum split-half correlation | 0.8827 | Correlation of averaged half profiles |
| Minimum available ICC(2,1) | 0.5486 | Below 0.60; five estimates, Claude not computable |
| Minimum cross-system correlation | 0.3189 | Mistral DIR/PER; below 0.60 |
| Historical human-labelled vs final score | κ = 0.5789 | 200 rows; no Claude coverage; coder provenance unverified |

These statistics measure different things. High agreement between LLM judges
is not evidence of representative human validation. Split-half averages are not
single-response reliability. Prompt framing is not the only weakness: the ICC
criterion also fails, and some ABS/DIR contrasts are below the cross-system
threshold.

The ten runs rotate several factors and are not a balanced test-retest design.
GPT-5.2 has an exception: omission of nominal temperature and `top_p` creates
opportunistic pairs of reconstructibly identical requests. This does not verify
provider/backend identity or turn the full campaign into a controlled retest.
The small, purposive item set, incomplete factor crossing, historical coding
provenance and unrecorded backend revisions limit inference. See the manuscript
for exploratory analyses and uncertainty; an insignificant test is not absence
of an effect.

## Install and test

Use **Python 3.12**. Run from the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r paper/requirements.lock.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m src.runner --help
```

Installation downloads public packages. The local tests block socket connections,
use temporary databases and require no API key. The version-pinned environment
includes analysis, tests and PDF rendering; it is a reproducibility snapshot,
not a cryptographic wheel lock. `requirements.txt` points to this same snapshot, so a default install cannot
silently select an unverified statistical API version.

## Reproduce locally

With the retained reference inputs available, one command recomputes the study
without network access, collection or provider scoring:

```bash
.venv/bin/python scripts/reproduce.py --output-dir artifacts/runs/review-01
```

The command requires a **new** output directory. It opens references read-only,
backs up SQLite consistently, analyzes disposable copies, compares the historical
reports at tolerance 10⁻⁸, and writes aggregated tables, figures and an audit.
Success means numerical reproduction; the scientific result remains **FAIL**.

The [reproduction guide](docs/REPRODUCING.md) covers expected checks, missing
inputs, rebuilding the manuscript and the effects of lower-level commands.
The [data guide](docs/DATA.md) distinguishes campaign data, human-labelled data,
aggregate results and material excluded from a presentation export.

## Repository map

| Path | Role |
|---|---|
| `src/`, `tests/` | Pipeline implementation and local tests |
| `config/` | Executed design, model identifiers, prompts, items, rubrics and workflow notes |
| `data/` | Retained campaign and validation evidence; raw material requires review before release |
| `outputs/` | Historical v3.1 reports and figures, kept at their original paths |
| `paper/` | Manuscript sources, verified aggregates, references, provenance and reading PDF |
| `scripts/` | Offline reproduction, output guards and presentation export |
| `docs/` | Reproduction, data, contribution and release guidance |
| `docs/archive/`, `artifacts/reproduction/` | Historical protocols and earlier reproduction snapshots |
| `artifacts/runs/`, `paper/build/` | Ignored, disposable outputs from new local runs |

Archived protocols and earlier reproduction snapshots are evidence of project
history, not alternate installation or campaign recipes. Current code/config
resolve operational details; changing the scientific method requires a separate
decision.

## Presentation and release status

The repository is prepared for local review. **Public release is pending author
name, affiliation, licence and data/disclosure decisions.** No identity or licence
has been invented. Coders, blinding, chronology and ethical declarations also need
facts from the research owner before stronger scientific claims or submission.
See [release preparation](docs/RELEASING.md) and [contributing](docs/CONTRIBUTING.md).

A curated local presentation export includes code, configuration, tests and the
manuscript's aggregate evidence. It omits raw databases, coded CSV, raw excerpts,
private reconstruction records, caches and Git history. It is not a complete
raw-data replication package. Preparing this export does not publish anything.
The working repository and its history still contain retained raw evidence;
`.gitignore` does not remove files already tracked in Git.
