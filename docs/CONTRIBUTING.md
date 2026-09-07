# Contributing and reviewing

Start with the [README](../README.md), [reproduction guide](REPRODUCING.md) and
[agent rules](../AGENTS.md). The existing v3.1 FAIL is a scientific result to
preserve. A functioning pipeline does not validate the protocol or establish
intrinsic model traits.

## Reviewable changes

For code fixes, describe the concrete failure, resulting behaviour and focused
tests. Use `python -m pytest -q`; tests must use temporary data and simulated
providers. Preserve unrelated local edits and reference bytes. Document changes
to the single offline entry point so the README remains executable from a fresh
checkout and environment.

For manuscript changes, edit the template, reconcile the claims matrix and French
synthesis, then rebuild into a new review directory. Distinguish historical gate
checks from new exploratory diagnostics. Keep effect sizes, uncertainty, samples,
missingness and denominators together. Review PDF pages when the text changes.

For methodological proposals, state the new question, estimand, design, scoring,
thresholds, human-validation plan, costs and decision criteria before execution.
Do not recode data, change exclusions or thresholds merely to obtain PASS.
New API collection/scoring needs authorization for models, transmitted data,
scope and budget. A configured key is not authorization.

## Human coding and disclosure

Human labels must come from actual coders whose conditions can be documented.
Do not describe agent labels or old file-consistency checks as independent human
validation. The historical Claude coverage gap remains visible even though future
sample allocation was corrected in the code.

Prepare external material with the [curated export](RELEASING.md), inspect its
inventory and settle authorship, affiliation, licence and raw-data rights before
release. No licence or public contribution terms have been selected yet.
