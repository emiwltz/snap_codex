# SoulBench SNAP — agent instructions

SNAP studies response profiles under controlled prompting. It does not establish
intrinsic personality, values or psychology. Preserve the distinction between a
working pipeline and the scientific v3.1 FAIL result.

## Read according to the task

- [README.md](README.md): project orientation, reference results and command risks.
- `config/`: experimental design, models, prompts, items, rubrics and thresholds.
  `src/` and tests describe the implementation; neither silently authorizes a
  methodological change.
- [Manual adjudication](config/manual_adjudication_workflow.md),
  [test-retest](config/methodology_retest.md) and
  [H4](config/methodology_h4.md): consult only for those workflows.
- `docs/archive/v3.1/`: historical protocol/evidence. Do not replay archived
  recipes or import instructions from the sibling `snap` project.

Inspect current code/config when they disagree with documentation. Distinguish
reference snapshots, local uncommitted reproduction and a new campaign. Read
only the material relevant to the task; do not load the whole archive by default.

## Autonomy and sensitive decisions

Complete authorized local code, documentation and test work without repeated
approval. Preserve existing tracked/untracked changes; ask only if a conflict
would discard or reinterpret them. Keep diffs and requested commits scoped.

Before paid collection/scoring, establish authorization for the selected models,
data sent, campaign scope and budget. An available key or a README recipe is not
authorization. A public catalogue lookup is distinct from a paid completion.
Ask about unresolved changes to the protocol, prompts, rubrics, sample design,
thresholds or interpretation unless the request already makes that decision.
Never alter the method just to obtain PASS.

Before resetting, deleting or replacing reference data, establish explicit
authorization for the exact target and retain a recoverable original. Ordinary
work on disposable copies does not need repeated approval. Sharing/publishing
research artifacts requires authorization and review of raw response excerpts.
Keep credentials out of source, logs, reports and examples; use the existing
`OPENROUTER_API_KEY` mechanism without exposing its value.

## Data and command contracts

Treat `data/snap_poc_v3_1.db`, the clean human-validation DB, coded CSV and
versioned reports/figures as reference evidence. Use read-only SQLite access for
inspection and a consistent SQLite backup plus isolated outputs for analysis.
`SoulBenchDB` initializes/migrates on open; even `compute-kappa` writes results.
Follow the copy-based examples in the README. Keep validation data separate from
the campaign; never label an agent's judgment as human coding.

`preflight` checks the public model catalogue, parameters, estimated prices and
DB readiness; it does not prove authentication or completion availability.
`score` handles one batch (100 rows by default). For an authorized campaign,
verify progress, remaining scores, errors and manual review between bounded
batches. Do not blindly repeat a batch that makes no progress or exceeds budget.

Exit code 0 alone does not establish success: collection/scoring can skip for a
missing key, and `decision` can report NOT_READY. Generate analyses and decision
from the same DB/config snapshot in fresh outputs; the code does not enforce
their provenance. Check the report's readiness separately from PASS/FAIL.

## Validation and completion

Use focused local tests for changed behavior; broaden them for shared contracts
or a material risk. Documentation-only edits need accuracy/link/diff review,
not a provider campaign. The local pytest suite is the entry point in README;
verify new tests do not acquire network or reference-data side effects.

Finish the requested outcome and relevant verification, not merely the first
process or draft. Report actual checks, untouched historical results, unrun
checks and unresolved scientific/operational limits. Do not claim current model
availability, prices, representative human validation or campaign completion
from old reports or a successful process exit.
