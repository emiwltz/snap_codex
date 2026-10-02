# SNAP manuscript

This directory holds an **English working preprint** of the existing v3.1
campaign and its **FAIL** result, without any inference of intrinsic
personality.

## Read and revise

1. [Manuscript](manuscript.md) and [reading PDF](output/pdf/snap_v3_1_manuscript.pdf).
2. [Claims matrix](CLAIMS.md), also as [CSV](claims.csv): computation, evidence
   and limits of each conclusion.
3. [Supplement](supplement.md): prompts, coding poles and numerical tables.
4. [Publication figures](../figures/README.md): one idea per figure, with the
   plotted values.
5. [Complementary experiment plan](EXPERIMENT_PLAN.md): priorities and decisions
   required before any new campaign.
6. [Provenance](PROVENANCE.md), [first-draft QA](QA.md),
   [bibliographic register](references.json) and [BibTeX](references.bib).

The editable text is `manuscript.template.md`. Automatic tables and the
bibliography are materialized in `manuscript.md`. The editorial correction made
during review acknowledges the opportunistic GPT-5.2 repetitions; it does not
turn the full schedule into a controlled test-retest and changes no threshold or
historical score.

## Reproduce and build a review copy

Install the Python 3.12 environment as described in the
[project README](../README.md), then from the repository root:

```bash
.venv/bin/python scripts/reproduce.py --output-dir artifacts/runs/review-01
.venv/bin/python paper/scripts/build_manuscript.py --results-dir artifacts/runs/review-01 --output-dir paper/build/review-01
```

Destinations must be new. Computations use consistent SQLite backups, with no
network access or provider scoring; the builder checks the hashes of the inputs
of that computation. The new PDF and related files are written under
`paper/build/review-01/`. The evidence retained in `paper/results/` is not
overwritten by these commands.

The [reproduction guide](../docs/REPRODUCING.md) describes the expected checks
and Poppler rendering for visual inspection. Hashes in the historical audit
refer to the code version of that computation; new runs carry their own audits.

## Review and release

The [cleanup record](../docs/CLEANUP.md) separates the first manuscript, kept at
commit `d9fa3de`, from later corrections and preparation tools. The
[data guide](../docs/DATA.md) and [coding provenance](../docs/CODING_PROVENANCE.md)
describe the provenance and incomplete coverage of the historical labels. The
[release guide](../docs/RELEASING.md) lists the remaining release decisions.

No agent coding is presented as human. Coder identity, independence and
blinding, the chronology and the ethics statement are stated only as far as the
author has declared or the files record them.
