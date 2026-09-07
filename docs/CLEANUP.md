# Repository cleanup and review inventory

Date: 6 September 2026. This is local preparation for review; nothing was pushed,
published or submitted and no new provider collection or scoring was run.

## Comparison state and recovery

The first manuscript and inherited working changes were recorded by the owner at
commit `d9fa3de` (`jsp`). The original checkout was separately recorded at
`4afe059`. Both commits are preserved; this cleanup does not amend, rebase or reset
them. The review diff is `git diff d9fa3de` plus new untracked files.

Before cleanup, a local inventory and ZIP captured all 113 useful files, including
reference data and the first manuscript. They remain in ignored
`paper/private/cleanup-20260906/`. The inventory was made before the owner saved
the commit and therefore records the earlier HEAD and uncommitted status; its
file hashes, together with `d9fa3de`, establish the actual comparison state. The
backup includes raw material and is deliberately excluded from presentation.

## What changed and why

| Area | Change | Reason / recoverable original |
|---|---|---|
| Root README | Replaced the long mixed narrative/recipe document with a project entry and links to dedicated guides | Removes repeated history and competing commands; original in `d9fa3de` and local backup |
| Documentation | Added reproduction, data, contribution and release guidance | Gives operational details and real scientific/disclosure limits a stable home |
| Installation | Root `requirements.txt` now points to the existing version-pinned manuscript environment | Prevents a default install silently upgrading the statistical API beyond the verified environment |
| Reproduction | Added one root entry, fresh-output validation and clear missing-input errors | Protects evidence and makes the offline path usable from a checkout |
| Old shell recipe | Replaced fixed-output, `cp`-based sequence with a compatibility wrapper | Removes an unsafe competing recipe while keeping the old command name usable |
| PDF builder | Requires an explicit verified results directory and writes to a fresh review directory | Prevents inadvertent replacement of the reading copy; checks input provenance |
| Tests | Blocks network connections by default; adds output/export boundary tests | Checks the actual data protection and packaging contracts |
| Export | Explicit file allowlist, excerpt/pattern/link checks, ZIP and hash manifest | Makes a reviewable presentation package without raw data or history |
| Git review | Marked PDF, PNG and database files as binary; allowed standard CSV CRLF without changing evidence bytes | Keeps diffs legible and preserves recorded files |
| Ignore rules | Added secrets, environments, caches and fresh run/build/export directories | Keeps runtime and local review products out of routine Git additions |
| Manuscript | Corrected the blanket statement about identical repetitions for GPT-5.2 | Incorporates independent audit without changing the historical method or verdict |
| Current provenance prose | Removed personal machine paths and clarified which execution each audit describes | Separates local reconstruction records from the presentation bundle |

No reference database, coded CSV, historical result or figure was deleted, moved
or replaced. The earlier `artifacts/reproduction/` snapshots stay in place with
a short status note; they are excluded from presentation to avoid duplicate result
entry points. Archival prose is kept intact and omitted from the presentation
bundle because it has not been reviewed for raw excerpts and obsolete recipes.
Private paths in those retained archival records are not claimed to be cleaned.

`src/db.py` and `tests/test_db.py`, including the inherited correction for future
sample allocation, remain unchanged. Configuration YAML, prompts, rubrics,
sampling design, scores and thresholds remain unchanged.

## Verification record

The current sources were verified as follows:

- **Fresh environment:** created Python 3.12.14 environments and installed all 50
  pinned packages with `uv pip install --offline -r requirements.txt` from the
  already available public-package cache. Also validated the root requirements
  indirection using `python -m pip install --no-index -r requirements.txt` against
  the populated environment; `python -m pip check` reports no broken requirements.
  The project's ignored `.venv/` is ready locally. A new download from PyPI and
  cross-platform installation were not repeated in this cleanup.
- **Tests from an extracted presentation bundle:** `python -m pytest -q` passed
  **47 tests**, with 12 warnings, in 13.26 seconds. The warnings are the known
  synthetic-analysis degeneracy/convergence warnings; no test accessed a real
  provider. The six focused output/export tests were rerun after the final
  allowlist-format adjustment and passed.
- **CLI:** `python -m src.runner --help` works in the extracted bundle. The shell
  compatibility wrapper also exposes the current reproduction help.
- **Missing-data behaviour:** reproduction in the extracted bundle exits 2,
  names the two databases, coded CSV and withheld raw diagnostic, and points to
  `docs/DATA.md`. It creates no analysis destination or substitute database.
- **Output preservation:** an actual attempt to use `paper/results` as a new
  reproduction destination exits 2. Tests also cover existing directories and
  symlink escapes. Reference bytes remain unchanged after these checks.
- **Numerical reproduction:** the final version of the changed reproduction
  script was run in the fresh environment into `artifacts/runs/cleanup-02`.
  All 18 checks are true; stability, sensitivity, variance and decision have zero
  differences at 10⁻⁸ tolerance, excluding generation timestamps. Readiness is
  complete and the scientific decision remains **FAIL**. The audit is copied to
  [the review evidence](../paper/review/reproduction_audit.json).
- **Added diagnostics:** all 180 pair memberships, code-agreement statistics and
  15 item agreement summaries match the independent computational auditor's
  results. This is computational agreement, not human validation.
- **PDF:** rebuilt with explicit fresh results into `paper/build/cleanup-01`,
  rendered with system Poppler at 110 dpi and inspected all 14 pages. No clipping,
  overlap or missing glyph was observed. The promoted reading manuscript has
  **6,524 Markdown words, five main tables, three figures and eight references**.
  Its checks are in [current document metadata](../paper/review/document_checks.json).
  The supplement also includes the per-item agreement table.
- **References preserved:** all **31** data/historical-output files match their
  before-cleanup hashes and the original checkout. All `src/` files, method YAML
  and `tests/test_db.py` remain identical. [The hash record](reference-integrity.json)
  includes the three principal input datasets. The entire pre-existing
  `paper/results/` directory is unchanged; its audits describe the first draft.
- **Diff and package hygiene:** `git diff --check`, Python compilation and Black
  checks pass on the new/changed scripts and tests. Credential-pattern inspection
  of tracked/current text files found no matches. The export passes its explicit
  inventory, path, exact-excerpt, personal-path and bundled-link checks; archive
  integrity and every exported SHA-256 are checked after extraction.

The first manuscript's full-file manifest and original QA metadata remain under
`paper/provenance/` and `paper/results/`, labelled as historical records. They are
not silently rewritten to pretend they describe the revised documents. The current
reading PDF and fresh analysis audit are identified under `paper/review/`. New
run directories and local backups are ignored and excluded from the export.

The final local bundle is generated at
`artifacts/exports/final-review/snap-presentation-review.zip`, with its manifest
beside it. Code/configuration/test files were exercised in the clean candidate
extraction; subsequent changes are review documentation, Git attributes and the
explicit allowlist's support for those attributes, covered by the focused checks.
No external delivery is implied by preparing this file.

## Remaining publication decisions

Only the research owner can supply author name, affiliation, licence choice,
raw-data/disclosure terms and actual coder/ethics/chronology facts. They are not
invented by cleanup. The scientific v3.1 FAIL is retained; a presentation-ready
repository is not evidence that the protocol passed or that independent human
validation has been established.
