#!/usr/bin/env python3
"""Independent, read-only candidate/ZIP review; outputs only in this audit tree."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "work/candidate-01"
EVIDENCE = ROOT / "docs/audit/evidence"


def sha(content):
    return hashlib.sha256(content).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def csv_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def norm(value):
    return " ".join(value.split())


def main():
    capture = read_json(CANDIDATE / "CAPTURE.json")
    source = Path(capture["source"])
    report = {"checked_utc": datetime.now(timezone.utc).isoformat(),
              "source_head_at_capture": capture["head"], "capture_utc": capture["captured_utc"]}
    report["source_changes_since_capture"] = [p for p, h in capture["files"].items()
        if not (source / p).is_file() or sha((source / p).read_bytes()) != h]
    report["source_current_head"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    report["candidate_non_database_changes"] = [p for p, h in capture["files"].items()
        if not p.endswith(".db") and (not (CANDIDATE / p).is_file() or sha((CANDIDATE / p).read_bytes()) != h)]
    report["integrated_audit_input_hash_errors"] = {}
    for name in ["audit_diagnostics.json", "reproduction_audit.json"]:
        audit = read_json(CANDIDATE / "paper/review" / name)
        report["integrated_audit_input_hash_errors"][name] = [p for p, h in audit["input_sha256"].items() if capture["files"].get(p) != h]

    original = read_json(EVIDENCE / "independent_results.json")["opportunistic_repeats"]
    added = read_json(CANDIDATE / "paper/review/audit_diagnostics.json")
    report["integrated_GPT_metrics_match"] = all([
        original["n"] == added["repeated_pairs"],
        original["run_pairs"] == added["run_pairs"],
        original["score_agreement"]["agreement"] == added["score_agreement"]["exact"],
        original["score_agreement"]["kappa"] == added["score_agreement"]["kappa"],
        original["score_pearson"] == added["score_pearson"],
        original["raw_equal"] == added["raw_text_equal"],
        original["n"] - original["prompt_tokens_equal"] == added["different_prompt_token_counts"],
        original["time_delta_seconds"] == added["storage_time_deltas_seconds"],
    ])
    old_pairs = csv_rows(EVIDENCE / "gpt52_opportunistic_pairs.csv")
    new_pairs = csv_rows(CANDIDATE / "paper/review/gpt52_opportunistic_pairs.csv")
    columns = set(old_pairs[0]) & set(new_pairs[0]) - {"request_signature"}
    canonical = lambda rows: sorted(tuple(r[k] for k in sorted(columns)) for r in rows)
    report["integrated_180_pairs_match"] = len(new_pairs) == 180 and canonical(old_pairs) == canonical(new_pairs)
    report["signature_comparison_note"] = "Hashes intentionally differ: independent script serializes internal model alias; integrated script serializes configured endpoint. Compare pair keys, scores, flags and times, not these serializations."
    old_items = {r["item"]: r for r in read_json(EVIDENCE / "item_agreement_screen.json")}
    new_items = csv_rows(CANDIDATE / "paper/review/item_agreement.csv")
    errors = []
    for r in new_items:
        old = old_items[r["item"]]
        kap = None if r["kappa"] == "" else float(r["kappa"])
        if not (int(r["n"]) == old["judge_pairs"] and float(r["exact"]) == old["exact_agreement"]
                and kap == old["kappa"] and json.loads(r["final_counts"]) == old["final_counts"]):
            errors.append(r["item"])
    report["integrated_item_comparison"] = {"items": len(new_items), "errors": errors}

    archive = ROOT / "work/final-presentation-review.zip"
    author_archive = source / "artifacts/exports/final-review/snap-presentation-review.zip"
    archive.write_bytes(author_archive.read_bytes())
    recipient = ROOT / "work/recipient-audit-final"
    recipient.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        names = [i.filename for i in entries]
        unsafe = [i.filename for i in entries if PurePosixPath(i.filename).is_absolute()
                  or ".." in PurePosixPath(i.filename).parts or not i.filename.startswith("snap-presentation/")
                  or stat.S_ISLNK(i.external_attr >> 16)]
        assert not unsafe and len(set(names)) == len(names)
        assert z.testzip() is None
        files = {n.removeprefix("snap-presentation/"): z.read(n) for n in names}
        z.extractall(recipient)
    manifest = json.loads(files["EXPORT_MANIFEST.json"])
    report["zip"] = {"path_relative_to_audit": str(archive.relative_to(ROOT)), "sha256": sha(archive.read_bytes()),
        "bytes": archive.stat().st_size, "file_count": len(files), "unsafe_paths": unsafe,
        "manifest_hash_mismatches": [p for p, h in manifest["files_sha256"].items() if sha(files[p]) != h],
        "files_not_in_hash_manifest": sorted(set(files) - set(manifest["files_sha256"])),
        "manifest_matches_sidecar": files["EXPORT_MANIFEST.json"] == (author_archive.parent / "EXPORT_MANIFEST.json").read_bytes(),
        "source_content_mismatches": [p for p in files if not p.startswith("EXPORT_") and files[p] != (source / p).read_bytes()],
        "forbidden_payloads": [p for p in files if p.startswith(("data/", ".git/", "paper/private/", "paper/provenance/", "docs/archive/"))
             or p.endswith((".db", ".sqlite", ".env")) or p == "outputs/reports/cross_sp_diagnostic.json"]}
    with zipfile.ZipFile(CANDIDATE / "artifacts/exports/audit-final/snap-presentation-review.zip") as old_zip:
        old_files = {n.removeprefix("snap-presentation/"): old_zip.read(n) for n in old_zip.namelist()}
    report["zip_delta_since_100_file_candidate"] = {"added": sorted(set(files) - set(old_files)),
        "removed": sorted(set(old_files) - set(files)),
        "changed": sorted(p for p in set(files) & set(old_files) if files[p] != old_files[p])}
    integrity = json.loads(files["docs/reference-integrity.json"])
    report["final_integrity_manifest"] = {"references": len(integrity["reference_sha256"]),
        "source_hash_errors": [p for p, h in integrity["reference_sha256"].items() if sha((source / p).read_bytes()) != h],
        "original_hash_errors": [p for p, h in integrity["reference_sha256"].items()
            if sha((Path('/Users/emi/code/side/snap_codex') / p).read_bytes()) != h]}

    secret = re.compile(r"(?:sk-(?:or-v1|proj)-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")
    personal = re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/")
    readables = {}
    for name, body in files.items():
        if name.endswith(".png"):
            continue
        if name.endswith(".pdf"):
            pdf = PdfReader(io.BytesIO(body))
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
            report["pdf"] = {"pages": len(pdf.pages), "sha256": sha(body), "metadata": dict(pdf.metadata),
                "visual_review": "All 14 pages inspected at 110 dpi. No clipping, overlap, missing glyph, raw response or personal path observed. Three numerical figures are also the three PNG figures in the archive.",
                "visual_review_date": "2026-09-06"}
        else:
            text = body.decode("utf-8")
            if name.endswith(".json"):
                text += "\n" + "\n".join(strings(json.loads(text)))
        readables[name] = text
    report["privacy_pattern_hits"] = {p: [label for label, rex in [("secret-pattern", secret), ("personal-absolute-path", personal)] if rex.search(t)]
        for p, t in readables.items() if secret.search(t) or personal.search(t)}

    # Match only retained response/justification text; never print any text or secrets.
    fragments = set()
    short_justifications = set()
    for name in ["snap_poc_v3_1.db", "snap_poc_v3_1_human_validation_clean.db"]:
        path = CANDIDATE / "data" / name
        with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
            conn.execute("PRAGMA query_only=ON")
            for row in conn.execute("SELECT raw_response,judge1_justification,judge2_justification FROM responses"):
                for value in row:
                    value = norm(value or "")
                    if len(value) >= 160:
                        fragments.update([value[:160], value[-160:], value[max(0, len(value)//2-80):len(value)//2+80]])
            for row in conn.execute("SELECT human_justification FROM manual_verification"):
                value = norm(row[0] or "")
                if len(value) >= 80:
                    short_justifications.add(value)
    report["exact_text_scan"] = {"long_fragments_checked": len(fragments), "manual_justifications_checked": len(short_justifications), "hits": [],
        "limit": "160-character normalized prefixes, midpoints and suffixes of responses and judge justifications; complete manual justifications >=80 characters. No semantic or legal assurance."}
    for name, text in readables.items():
        compact = norm(text)
        if any(f in compact for f in fragments) or any(f in compact for f in short_justifications):
            report["exact_text_scan"]["hits"].append(name)

    missing_links = []
    for name, text in readables.items():
        if not name.endswith(".md"):
            continue
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            target = target.split("#", 1)[0].strip("<>")
            if not target or re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            expected = os.path.normpath(str(PurePosixPath(name).parent / target))
            if expected not in files:
                missing_links.append({"file": name, "target": target})
    report["bundled_markdown_missing_files"] = missing_links
    root = recipient / "snap-presentation"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MPLCONFIGDIR=str(ROOT / "work/matplotlib"), XDG_CACHE_HOME=str(ROOT / "work/cache"))
    result = subprocess.run([sys.executable, "scripts/reproduce.py", "--output-dir", "artifacts/runs/missing-input-test"],
        cwd=root, env=env, text=True, capture_output=True)
    report["recipient_missing_input"] = {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
        "output_exists": (root / "artifacts/runs/missing-input-test").exists(), "private_directory_exists": (root / "paper/private").exists()}
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "tests/test_export_presentation.py", "tests/test_local_paths.py"], cwd=root, env=env, text=True, capture_output=True)
    report["recipient_final_targeted_tests"] = {"exit_code": tests.returncode, "stdout": tests.stdout, "stderr": tests.stderr}
    EVIDENCE.joinpath("candidate_capture_manifest.json").write_text(json.dumps(capture, indent=2) + "\n")
    EVIDENCE.joinpath("final_candidate_checks.json").write_text(json.dumps(report, indent=2) + "\n")
    EVIDENCE.joinpath("final_export_manifest.json").write_bytes(files["EXPORT_MANIFEST.json"])
    for name in ["pytest_candidate.log", "export_candidate.log"]:
        EVIDENCE.joinpath(name).write_bytes((ROOT / "work" / name).read_bytes())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
