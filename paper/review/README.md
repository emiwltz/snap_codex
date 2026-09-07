# Diagnostics added during repository review

These exploratory checks address findings from an independent computational audit
on 6 September 2026. They are not human coding, peer-review approval, a new campaign
or additional pass/fail criteria. The historical scores and v3.1 FAIL are unchanged.

- [Current manuscript document checks](document_checks.json): the revised reading PDF, its source hash and visual QA; the older `paper/results/document_checks.json` belongs to the first draft.
- [Fresh core reproduction audit](reproduction_audit.json): current code inputs and zero archived differences, with the retained FAIL.
- [Diagnostic audit](audit_diagnostics.json): inputs, request-reconstruction scope,
  aggregate repeat metrics and source-integrity check.
- [180 opportunistic GPT-5.2 pairs](gpt52_opportunistic_pairs.csv): conditions,
  score pairs, equality indicators and storage-timestamp separation; no raw text.
- [Agreement for each item](item_agreement.csv): complete judge-pair denominators,
  exact agreement, nominal kappa and final-score category counts.

Reproduce using the installed environment, with retained raw inputs available:

```bash
.venv/bin/python paper/scripts/audit_diagnostics.py --output-dir artifacts/runs/diagnostics-01
```

The script independently implements nominal kappa and request grouping without
importing SNAP statistical functions. Grouping uses stored messages and sent/
omitted flags; the endpoint, `max_tokens` and applicable `top_p` come from retained
configuration/code. This cannot attest unrecorded backend routing or all provider
execution details. In particular, two of the 180 pairs have different recorded
prompt-token counts. The request hash serialization differs from the independent
auditor's internal model-alias serialization; the pair memberships and metrics
were checked to agree.

For E1, both judges and the final score are +1 on all 180 responses. Exact agreement
is 100%; nominal kappa is undefined because expected agreement is also 100%.
No criterion was applied to discard or recode these responses. Five of fourteen
finite item kappas are below 0.60; this is descriptive comparison with a familiar
reference value, not a newly imposed per-item decision gate.

Local Git chronology was also checked: commit `0646789` carries the same run
schedule and decision-threshold mapping as the current configuration and has
local author/committer timestamps of 10 May 2026, before the first retained
responses on 12 May. Commit `be15135` on 24 April already has the same schedule,
but its full threshold mapping differs. Local mutable timestamps support a
bounded historical account, not independent immutable preregistration.
