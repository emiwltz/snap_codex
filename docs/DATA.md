# Data, evidence and availability

The research object is a response under a recorded condition. A label describes
that response relative to an item's poles; it is not a universal good/bad score
or an observation of intrinsic model personality.

## Retained inputs and outputs

| Location | Content | Status |
|---|---|---|
| `data/snap_poc_v3_1.db` | 2,700 campaign responses, prompts, scores, justifications and collection metadata | Raw reference; read-only inspection |
| `data/snap_poc_v3_1_human_validation_clean.db` | Separate validation reference sharing campaign responses and historical human-labelled codes | Raw reference; not an independent collection |
| `data/manual_sample_coded.csv` | 200 historical coded rows | Raw validation reference; exact correspondence audited |
| `config/*.yaml` | Executed design, nominal settings, items and rubrics | Method reference; do not alter to improve the verdict |
| `outputs/reports/`, `outputs/figures/` | Historical v3.1 reports and figures | Preserved at original paths |
| `outputs/reports/cross_sp_diagnostic.json` | Aggregates **and raw response excerpts** | Excluded from the presentation export |
| `paper/results/` | Audited manuscript aggregates and numerical supplements | Retained first-manuscript evidence |
| `artifacts/reproduction/` | Earlier local reproductions | Historical comparisons, not a new campaign |
| `artifacts/runs/` | Newly recomputed aggregates | Disposable, ignored; each run records its own inputs |

The working Git history contains raw data. Ignoring future database files does not
untrack existing evidence. Do not publish the full history on the assumption that
it has the same scope as the manuscript or presentation bundle.

## Schema and joins

`responses.trial_id` identifies each trial. Recorded factors include model, item,
scenario, formulation, system condition, nominal temperature and scheduled run.
`temperature_applied` and `top_p_applied` distinguish requested settings from
nominal design values; null does not establish a known provider default. Recorded
collection seeds control condition ordering, not provider sampling.

`score_judge1`, `score_judge2` and `score_final` are distinct measurements. Labels
are `+1`, `0`, `-1` and `REFUS`, interpreted against the item's rubric. Numerical
analyses exclude errors and refusals. All 2,700 trials have final scores, but five
second-judge scores are absent; nominal inter-judge agreement uses 2,695 pairs.
Seventeen responses retain truncation flags and are separately examined in
exploratory sensitivity analyses.

Validation rows are linked back to campaign responses and CSV labels during
reproduction. The 200 historical human-labelled rows cover five models and exclude
Claude. Coder identity, independence, blinding and inter-human reliability are not
established by file consistency. No agent-generated judgment is called human
coding.

## Provenance and reproducibility

The [manuscript provenance](../paper/PROVENANCE.md) records the initial source
commit, imported local corrections and analysis chain. `paper/results/audit.json`
records input SHA-256 hashes, backup hashes, environment and reference comparisons
for the first draft. A new reproduction records a fresh audit beside its outputs.
The historical audit remains evidence of its original execution; it is not a claim
that today's scripts have their former hashes.

The [reference hash record](reference-integrity.json) verifies the retained files.
The [cleanup inventory](CLEANUP.md) identifies the current comparison commit and
what was changed. Reference data and historical outputs are kept byte-identical.
Scientific interpretation still requires the methodological and human-provenance
limitations described in the manuscript.

## Presentation bundle and missing data

The curated export contains code, configuration, tests, manuscript, bibliography
and selected aggregate evidence. It excludes the two databases, coded CSV, raw
response diagnostic, archival prose not reviewed for excerpts, private import
records and Git history. Data rights and disclosure have not been decided, so no
raw download is claimed and no author/contact identity is invented.

A recipient can run the local tests and inspect aggregate results. Full numerical
reproduction requires the exact retained inputs at the paths above, obtained only
through a separately approved release/access process. The reproduction command
fails with a clear missing-input error when they are absent. It does not fabricate
samples, fetch private data or silently switch to a demonstration dataset.
