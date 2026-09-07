#!/usr/bin/env python3
"""Expand evidence-bound manuscript tables, bibliography and review PDF offline."""

from __future__ import annotations
import argparse
import os
import shutil
import sys
import csv
import hashlib
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "paper/private/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / "paper/private/cache"))
from scripts.local_paths import fresh_directory

import pandas as pd
import yaml
import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
)
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
RESULTS = PAPER / "results"
BUILD = PAPER / "build/review"
LABELS = {
    "claude-sonnet-4-5": "Claude Sonnet 4.5",
    "gemini-3-pro": "Gemini 3.1 Pro",
    "gpt-5-2": "GPT 5.2",
    "grok-4-3": "Grok 4.3",
    "mistral-large-3": "Mistral Large 3",
    "qwen3-max": "Qwen3 Max",
}


def table(headers, rows):
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        + ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    )


def fmt(value):
    return "Not computable" if pd.isna(value) else f"{value:.4f}"


def percent(value):
    return f"{100*value:.2f}%"


def expand():
    audit = json.loads((RESULTS / "audit.json").read_text())
    assert all(audit["checks"].values()), "Fix failed audit checks first"
    for rel, expected in audit["input_sha256"].items():
        assert (
            hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == expected
        ), f"Stale evidence: {rel}"
    assert all(
        not v for v in audit["archived_comparison"].values()
    ), "Review changed archived analyses before rendering"
    review_audit = json.loads((PAPER / "review/audit_diagnostics.json").read_text())
    for rel, expected in review_audit["input_sha256"].items():
        assert (
            hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == expected
        ), f"Stale review diagnostics: {rel}"
    m = json.loads((RESULTS / "metrics.json").read_text())
    d = json.loads((RESULTS / "core/decision_report.json").read_text())
    reliability = pd.read_csv(RESULTS / "reliability.csv")
    cross = pd.read_csv(RESULTS / "cross_sp.csv")
    sensitivity = pd.read_csv(RESULTS / "sensitivity_scoring_truncation.csv")
    critical = cross[
        (cross.model == "mistral-large-3") & (cross.pair == "SP_DIR_vs_SP_PER")
    ].iloc[0]
    selected = sensitivity[
        (sensitivity.model == "mistral-large-3")
        & (sensitivity.pair == "SP_DIR_vs_SP_PER")
    ].set_index("analysis")
    ci = json.loads(critical.pearson_item_run_95ci_item_cluster_bootstrap)
    mapping = {
        "judge_kappa": fmt(m["judge_agreement"]["unweighted_kappa"]),
        "split_min": fmt(reliability.split_half.min()),
        "split_max": fmt(reliability.split_half.max()),
        "icc_min": fmt(reliability.icc2.min()),
        "cross_min": fmt(m["minimum_cross_sp"]),
        "human_final_kappa": fmt(
            m["human_validation"]["human_vs_final"]["unweighted_kappa"]
        ),
        "major_rate": percent(d["checks"][2]["value"]),
        "critical_cross_ci": f"[{ci[0]:.4f}, {ci[1]:.4f}]",
        "critical_itemmean_r": fmt(critical.pearson_item_means_n15),
        "critical_centered_r": fmt(critical.within_item_centered_pearson),
        "critical_exact": percent(critical.exact_agreement),
        "critical_mad": fmt(critical.mean_absolute_difference),
        "mistral_without_truncation": fmt(selected.loc["exclude_truncated", "pearson"]),
        "mistral_without_truncation_n": str(
            int(selected.loc["exclude_truncated", "n_pairs"])
        ),
        "mistral_judge1": fmt(selected.loc["judge1_only", "pearson"]),
        "mistral_judge2": fmt(selected.loc["judge2_only", "pearson"]),
        "holm_min": fmt(
            pd.read_csv(RESULTS / "sensitivity_multiplicity.csv").p_holm_all_17.min()
        ),
        "eta_item": fmt(m["variance_eta_squared"]["item_id"]),
        "eta_model": fmt(m["variance_eta_squared"]["model"]),
        "eta_sp": fmt(m["variance_eta_squared"]["system_prompt"]),
    }
    schedule = pd.read_csv(RESULTS / "run_schedule.csv")
    mapping["table_schedule"] = table(
        ["Run", "Scenario", "Formulation", "Nominal temperature"],
        schedule.values.tolist(),
    )
    cfg = yaml.safe_load((ROOT / "config/models.yaml").read_text())
    mapping["table_models"] = table(
        ["Label", "Configured OpenRouter identifier", "N"],
        [
            [model["label"], model["openrouter_model_id"], 450]
            for model in cfg["models"]
            if model["active"]
        ],
    )
    agreement_rows = [["Judge1 vs judge2", m["judge_agreement"]]]
    agreement_rows += [
        [name, m["human_validation"][key]]
        for name, key in [
            ("Historical human vs judge1", "human_vs_judge1"),
            ("Historical human vs judge2", "human_vs_judge2"),
            ("Historical human vs final", "human_vs_final"),
        ]
    ]
    mapping["table_agreement"] = table(
        ["Comparison", "Pairs", "Exact agreement", "Unweighted kappa"],
        [
            [
                n,
                row["n_pairs"],
                percent(row["exact_agreement"]),
                fmt(row["unweighted_kappa"]),
            ]
            for n, row in agreement_rows
        ],
    )
    names = [
        "Inter-judge kappa",
        "Refusal rate",
        "Initial major-disagreement rate",
        "Minimum model ICC (5 available)",
        "Minimum model split-half (6)",
        "Minimum cross-system r (18 pairs)",
    ]
    gates = [
        ">=0.60 target; >=0.50 floor",
        "<=0.10",
        "<=0.15",
        ">=0.60",
        ">=0.60",
        ">=0.60",
    ]
    mapping["table_decision"] = table(
        ["Check", "Value", "Rule", "Status"],
        [
            [name, fmt(row["value"]), gate, row["status"].upper()]
            for name, gate, row in zip(names, gates, d["checks"])
        ],
    )
    mapping["table_reliability"] = table(
        ["Model", "ICC(2,1)", "Split-half r", "Lowest cross-system r"],
        [
            [LABELS[r.model], fmt(r.icc2), fmt(r.split_half), fmt(r.minimum_cross_sp)]
            for r in reliability.itertuples()
        ],
    )
    references = json.loads((PAPER / "references.json").read_text())
    bibliography = []
    for index, r in enumerate(references, 1):
        bibliography.append(
            f"[{index}] {r['authors']} ({r['year']}). {r['title']}. {r['venue']}. [DOI: {r['doi']}](https://doi.org/{r['doi']})."
        )
    mapping["references"] = "\n\n".join(bibliography)
    source = (PAPER / "manuscript.template.md").read_text()
    for key, value in mapping.items():
        source = source.replace("{{" + key + "}}", value)
    for index, r in enumerate(references, 1):
        assert f"[{r['id']}]" in source, f"Uncited reference {r['id']}"
        source = source.replace(f"[{r['id']}]", f"[{index}]")
    assert not re.search(
        r"\{\{.*?\}\}|\[(?:huang|serapio|sandhan|zierahn|zheng|cohen|koo|graham)\d+\]",
        source,
    )
    (BUILD / "manuscript.md").write_text(source)
    bib = []
    for r in references:
        authors = r["authors"].replace(", and ", " and ").replace(", ", " and ")
        kind = (
            "misc"
            if "arXiv" in r["venue"]
            else ("inproceedings" if "EMNLP" in r["venue"] else "article")
        )
        bib.append(
            f"@{kind}{{{r['id']},\n  author = {{{authors}}},\n  title = {{{r['title']}}},\n  year = {{{r['year']}}},\n  doi = {{{r['doi']}}},\n  url = {{{r['url']}}},\n  note = {{{r['venue']}}}\n}}"
        )
    (BUILD / "references.bib").write_text("\n\n".join(bib) + "\n")
    supplement = [
        "# Supplementary material - SoulBench SNAP v3.1",
        "",
        "This supplement contains constructed input prompts and numerical summaries only. It contains no raw model responses or coder justifications.",
        "",
        "## Exact system conditions",
        "",
    ]
    for key, value in yaml.safe_load((ROOT / "config/system_prompts.yaml").read_text())[
        "system_prompts"
    ].items():
        supplement += [
            "### " + key,
            "",
            value.strip() if value else "No system message is sent.",
            "",
        ]
    supplement += [
        "## Item poles",
        "",
        "Descriptions below are generated from the active rubric file. The numeric signs do not share a common evaluative meaning across items.",
        "",
    ]
    for key, obj in yaml.safe_load((ROOT / "config/scoring_rubrics.yaml").read_text())[
        "rubrics"
    ].items():
        supplement += ["### " + key, "", obj["description"], ""]
    review_rows = list(csv.DictReader((PAPER / "review/item_agreement.csv").open()))
    supplement += [
        "## Exploratory agreement by item",
        "",
        "The global coefficient does not imply uniform coding agreement. No new decision gate is imposed. Blank/undefined kappa denotes constant marginals, not failed data processing.",
        "",
        table(
            ["Item", "Judge pairs", "Exact agreement", "Nominal kappa"],
            [
                [
                    r["item"],
                    r["n"],
                    percent(float(r["exact"])),
                    fmt(float(r["kappa"])) if r["kappa"] else "Undefined",
                ]
                for r in review_rows
            ],
        ),
        "",
        "E1 has +1 from both judges and as final score on all 180 responses. Its kappa is undefined because expected agreement is 100%. It does not discriminate models or prompts in this corpus. See the [review diagnostic definitions and provenance](review/README.md), [item counts](review/item_agreement.csv), and [180 opportunistic GPT-5.2 pairs](review/gpt52_opportunistic_pairs.csv).",
        "",
    ]
    supplement += [
        "## Numerical supplements",
        "",
        "- [All 18 cross-system pairs, aggregation diagnostics and bootstrap bounds](results/cross_sp.csv)",
        "- [Split-half uncertainty and constant-target fractions](results/split_half.csv)",
        "- [Every item-system-model mean and numeric count](results/item_prompt_means.csv)",
        "- [Historical human-validation coverage](results/human_coverage.csv)",
        "- [All 17 unadjusted tests and post-hoc Holm corrections](results/sensitivity_multiplicity.csv)",
        "- [Truncation and judge-only scoring sensitivity](results/sensitivity_scoring_truncation.csv)",
        "- [Model collection dates and seeds](results/model_metadata.csv)",
        "- [Detailed agreement and selected-cell exploratory diagnostics](results/metrics.json)",
        "- [Input hashes, versions, audits and archived-report comparison](results/audit.json)",
        "",
        "The paired-run sign-flip p-values in metrics.json inherit a post-selected-cell analysis and are not calibrated confirmatory evidence. The deterministic schedule is not a verified random exchangeable sample. Weighted kappas use ordinal-only pairs and are not comparable to the nominal four-category coefficient without considering their different populations and weights.",
        "",
    ]
    (BUILD / "supplement.md").write_text("\n".join(supplement))
    return source


def inline(text):
    text = html.escape(text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" color="#345c74">\1</a>', text
    )
    text = re.sub(r"`([^`]+)`", r'<font name="Sans" size="9">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    return text


def render(source):
    fonts = Path(matplotlib.get_data_path()) / "fonts/ttf"
    for name, filename in [
        ("Serif", "DejaVuSerif.ttf"),
        ("Serif-Bold", "DejaVuSerif-Bold.ttf"),
        ("Serif-Italic", "DejaVuSerif-Italic.ttf"),
        ("Serif-BoldItalic", "DejaVuSerif-BoldItalic.ttf"),
        ("Sans", "DejaVuSans.ttf"),
        ("Sans-Bold", "DejaVuSans-Bold.ttf"),
    ]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    pdfmetrics.registerFontFamily(
        "Serif",
        normal="Serif",
        bold="Serif-Bold",
        italic="Serif-Italic",
        boldItalic="Serif-BoldItalic",
    )
    pdfmetrics.registerFontFamily(
        "Sans", normal="Sans", bold="Sans-Bold", italic="Sans", boldItalic="Sans-Bold"
    )
    body = ParagraphStyle(
        "body",
        fontName="Serif",
        fontSize=10,
        leading=14,
        spaceAfter=7,
        allowWidows=0,
        allowOrphans=0,
    )
    heading = ParagraphStyle(
        "heading",
        fontName="Sans-Bold",
        fontSize=12.3,
        leading=16,
        spaceBefore=12,
        spaceAfter=7,
        keepWithNext=True,
    )
    subheading = ParagraphStyle(
        "subheading", parent=heading, fontSize=10.8, leading=14, spaceBefore=8
    )
    title = ParagraphStyle(
        "title",
        fontName="Serif-Bold",
        fontSize=21,
        leading=26,
        spaceAfter=16,
        keepWithNext=True,
    )
    small = ParagraphStyle("small", parent=body, fontSize=8.3, leading=11, spaceAfter=7)
    cell = ParagraphStyle(
        "cell", fontName="Sans", fontSize=8.3, leading=11, spaceAfter=0
    )
    page_width, page_height = A4
    width = page_width - 104
    content = []
    lines = source.splitlines()
    i = 0
    table_number = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("# "):
            content.append(Paragraph(inline(line[2:]), title))
        elif line.startswith("## "):
            content.append(Paragraph(inline(line[3:]), heading))
        elif line.startswith("### "):
            content.append(Paragraph(inline(line[4:]), subheading))
        elif line.startswith("!["):
            path = re.search(r"\]\(([^)]+)\)", line).group(1)
            im = Image(str(BUILD / path))
            im.drawHeight = width * im.imageHeight / im.imageWidth
            im.drawWidth = width
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            elements = [Spacer(1, 4), im, Spacer(1, 6)]
            if j < len(lines) and lines[j].startswith("*Figure "):
                elements.append(Paragraph(inline(lines[j]), small))
                i = j
            content.append(KeepTogether(elements))
        elif line.startswith("| "):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.fullmatch(r"[| :\-]+", lines[i].strip()):
                    rows.append(
                        [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    )
                i += 1
            i -= 1
            table_number += 1
            proportions = {
                1: [0.11, 0.27, 0.25, 0.37],
                2: [0.30, 0.61, 0.09],
                3: [0.43, 0.10, 0.24, 0.23],
                4: [0.45, 0.14, 0.27, 0.14],
                5: [0.33, 0.21, 0.20, 0.26],
            }
            widths = [width * p for p in proportions[table_number]]
            cells = [
                [
                    Paragraph(
                        ("<b>" if n == 0 else "")
                        + inline(x)
                        + ("</b>" if n == 0 else ""),
                        cell,
                    )
                    for x in row
                ]
                for n, row in enumerate(rows)
            ]
            tab = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
            tab.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef1")),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#788b96")),
                        (
                            "LINEBELOW",
                            (0, -1),
                            (-1, -1),
                            0.5,
                            colors.HexColor("#788b96"),
                        ),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f6f7f8")],
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            content.extend([tab, Spacer(1, 9)])
        elif line.startswith("- "):
            content.append(Paragraph(inline(line[2:]), body, bulletText="-"))
        else:
            if line.startswith("**Table "):
                style = ParagraphStyle("caption", parent=small, keepWithNext=True)
            elif re.match(r"\[\d+\] ", line):
                style = small
            else:
                style = body
            content.append(Paragraph(inline(line), style))
        i += 1

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Sans", 7.5)
        canvas.setFillColor(colors.HexColor("#5d6870"))
        canvas.drawString(
            52, 26, "SoulBench SNAP v3.1 | Working preprint | 6 September 2026"
        )
        canvas.drawRightString(page_width - 52, 26, str(doc.page))
        canvas.restoreState()

    pdf = BUILD / "output/pdf/snap_v3_1_manuscript.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(pdf),
        pagesize=A4,
        rightMargin=52,
        leftMargin=52,
        topMargin=45,
        bottomMargin=45,
        title="Scorable yet context-sensitive: SoulBench SNAP v3.1",
        author="Authorship pending research-owner approval",
        subject="Local scientific working draft; historical POC FAIL; no new collection",
    )
    doc.build(content, onFirstPage=footer, onLaterPages=footer)
    reader = PdfReader(pdf)
    extracted = "\n".join(page.extract_text() for page in reader.pages)
    for fragment in [
        "Abstract",
        "FAIL",
        "0.7509",
        "0.3189",
        "References",
        "Declarations to complete",
    ]:
        assert fragment in extracted, fragment
    assert len(reader.pages) >= 8
    qa = BUILD / "qa"
    qa.mkdir(exist_ok=True)
    (qa / "pdf_text.txt").write_text(extracted)
    checks = {
        "pages": len(reader.pages),
        "words_markdown": len(source.split()),
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "manuscript_sha256": hashlib.sha256(
            (BUILD / "manuscript.md").read_bytes()
        ).hexdigest(),
        "tables": table_number,
        "figures": source.count("![Figure"),
        "references": len(json.loads((PAPER / "references.json").read_text())),
        "text_checks": "passed",
        "visual_review": "required after rendering pages",
    }
    (BUILD / "results/document_checks.json").write_text(
        json.dumps(checks, indent=2) + "\n"
    )
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="Fresh results from scripts/reproduce.py",
    )
    parser.add_argument("--output-dir", type=Path, default=BUILD)
    args = parser.parse_args()
    RESULTS = args.results_dir.resolve()
    if not (RESULTS / "audit.json").is_file():
        parser.error("Missing audit.json; run scripts/reproduce.py first")
    try:
        BUILD = fresh_directory(args.output_dir, ROOT, ("paper/build",))
    except ValueError as error:
        parser.error(str(error))
    shutil.copytree(RESULTS, BUILD / "results")
    shutil.copytree(PAPER / "review", BUILD / "review")
    render(expand())
