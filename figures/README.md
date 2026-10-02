# Publication figures

One idea per figure. Each figure is provided as PDF (vector, for the article),
PNG (reading copy) and the CSV of the plotted values.

| Figure | Idea | Inputs |
|---|---|---|
| `fig1_design` | The unit of analysis is a coded response under a recorded condition; 6 × 15 × 3 × 10 = 2,700, runs rotate factors and are not identical repetitions. | `metrics.json`, `core/decision_report.json` |
| `fig2_verdict` | The judges agree (κ = 0.75), but per-model stability (ICC) and prompt robustness fall below the pre-set 0.60 minimum: the decision is FAIL. | `core/decision_report.json`, `reliability.csv`, `cross_sp.csv` |
| `fig3_cross_prompt` | Changing the system prompt shifts response profiles unevenly: 6 of 18 model-prompt pairs fall below r = 0.60, worst Mistral Large 3 neutral vs persona (r = 0.32). | `cross_sp.csv` (item-cluster bootstrap 95% intervals) |
| `fig4_items` | Pooled agreement hides item heterogeneity: five items have κ below 0.60 and E1 is coded +1 for all 180 responses (κ undefined). | `paper/review/item_agreement.csv` |

The figures read aggregate results only. To rebuild them from the retained
manuscript aggregates:

```bash
.venv/bin/python paper/scripts/make_figures.py --results-dir paper/results --output-dir figures
```

or from a fresh reproduction (see [REPRODUCING](../docs/REPRODUCING.md)):

```bash
.venv/bin/python scripts/reproduce.py --output-dir artifacts/runs/review-01
.venv/bin/python paper/scripts/make_figures.py --results-dir artifacts/runs/review-01 --output-dir artifacts/runs/review-01/publication-figures
```

Both inputs give identical figure data: on 3 October 2026 a reproduction in a
fresh clone matched `paper/results/` with no difference at tolerance 10⁻⁸.

Figures are released under [CC BY 4.0](../LICENSE-CC-BY-4.0.txt).
