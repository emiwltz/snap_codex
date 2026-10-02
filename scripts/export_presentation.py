#!/usr/bin/env python3
"""Prepare an explicit, locally reviewed presentation bundle. Never publish it."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.local_paths import fresh_directory

MANIFEST = ROOT / "docs/presentation-files.txt"
SECRET = re.compile(
    r"(?:sk-(?:or-v1|proj)-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
PERSONAL = re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/")
FORBIDDEN_PARTS = {".git", ".venv", "venv", "__pycache__", "private", "qa"}
FORBIDDEN_PREFIXES = ("data/", "docs/archive/", "artifacts/", "paper/provenance/")
FORBIDDEN_FILES = {"outputs/reports/cross_sp_diagnostic.json"}
# Documentation inside forbidden directories; contains no raw records.
ALLOWED_FILES = {"data/README.md", "data/DICTIONARY.md"}
ALLOWED_NAMES = {".gitignore", ".gitattributes", "LICENSE", "CITATION.cff"}
ALLOWED_SUFFIXES = {
    ".py",
    ".sh",
    ".md",
    ".txt",
    ".yaml",
    ".json",
    ".csv",
    ".bib",
    ".png",
    ".svg",
    ".pdf",
}


def candidates(root: Path, manifest: Path) -> list[Path]:
    result = []
    for line in manifest.read_text().splitlines():
        rel = line.strip()
        if not rel or rel.startswith("#"):
            continue
        path = root / rel
        parts = Path(rel).parts
        if (
            Path(rel).is_absolute()
            or ".." in parts
            or any(p in FORBIDDEN_PARTS for p in parts)
            or (rel.startswith(FORBIDDEN_PREFIXES) and rel not in ALLOWED_FILES)
            or rel in FORBIDDEN_FILES
            or (path.suffix not in ALLOWED_SUFFIXES and path.name not in ALLOWED_NAMES)
            or path.name.startswith(".env")
        ):
            raise ValueError(f"Forbidden export path: {rel}")
        if (
            not path.is_file()
            or any(
                (root.joinpath(*parts[:i])).is_symlink()
                for i in range(1, len(parts) + 1)
            )
            or not path.resolve().is_relative_to(root.resolve())
        ):
            raise ValueError(f"Missing or linked export file: {rel}")
        if path in result:
            raise ValueError(f"Duplicate export path: {rel}")
        result.append(path)
    return result


def normalize(text: str) -> str:
    return " ".join(text.split())


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def readable(path: Path, content: bytes) -> str:
    if path.suffix == ".png":
        return ""
    if path.suffix == ".pdf":
        from pypdf import PdfReader

        return "\n".join(
            p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages
        )
    text = content.decode("utf-8")
    if path.suffix == ".json":
        text += "\n" + "\n".join(strings(json.loads(text)))
    return text


def reference_fragments(root: Path) -> set[str]:
    source = root / "data/snap_poc_v3_1.db"
    if not source.is_file():
        raise ValueError(
            "Raw reference required for the local excerpt scan; see docs/DATA.md"
        )
    with sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        rows = conn.execute(
            "SELECT raw_response, judge1_justification, judge2_justification FROM responses"
        )
        return {
            normalize(value)[:160]
            for row in rows
            for value in row
            if value and len(normalize(value)) >= 160
        }


def scan(path: Path, content: bytes, fragments: set[str]) -> list[str]:
    text = readable(path, content)
    problems = []
    if SECRET.search(text):
        problems.append("credential-pattern")
    if PERSONAL.search(text):
        problems.append("personal-absolute-path")
    compact = normalize(text)
    if any(fragment in compact for fragment in fragments):
        problems.append("raw-response-or-judge-excerpt")
    return problems


def local_links(paths: list[Path], root: Path) -> list[str]:
    included = {path.resolve() for path in paths}
    failures = []
    for path in paths:
        if path.suffix != ".md":
            continue
        # Ignore code fences, where examples are not rendered as links.
        text = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            target = target.split("#", 1)[0].strip("<>")
            if not target or re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            if (path.parent / target).resolve() not in included:
                failures.append(
                    f"{path.relative_to(root)}: missing bundled link {target}"
                )
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "artifacts/exports/review"
    )
    args = parser.parse_args()
    try:
        paths = candidates(ROOT, MANIFEST)
        fragments = reference_fragments(ROOT)
        files = {str(path.relative_to(ROOT)): path.read_bytes() for path in paths}
        failures = {
            rel: issues
            for rel, content in files.items()
            if (issues := scan(Path(rel), content, fragments))
        }
        links = local_links(paths, ROOT)
        if failures or links:
            print(
                json.dumps(
                    {"rejected_files": failures, "broken_links": links}, indent=2
                )
            )
            raise ValueError("Export review checks failed; no archive written")
        out = fresh_directory(args.output_dir, ROOT, ("artifacts/exports",))
    except (ValueError, UnicodeDecodeError) as error:
        parser.error(str(error))
    notice = (
        "# Local presentation bundle - release pending\n\n"
        "Prepared for review only. No public release, licence, author name or affiliation "
        "has been approved. See docs/RELEASING.md.\n\n"
        "Raw databases, coded CSV, raw-response diagnostic, archival prose, private "
        "reconstruction records, runtime and Git history are omitted. Tests and aggregate "
        "inspection are available; full numerical reproduction requires the retained "
        "reference inputs described in docs/DATA.md.\n"
    ).encode()
    files["EXPORT_NOTICE.md"] = notice
    hashes = {
        rel: hashlib.sha256(content).hexdigest() for rel, content in files.items()
    }
    manifest = {
        "status": "local_review_only_release_pending",
        "files_sha256": hashes,
        "checks": {
            "allowlist": True,
            "no_symlinks": True,
            "known_secret_patterns": True,
            "personal_paths": True,
            "exact_reference_prefix_scan": True,
            "bundled_markdown_links": True,
        },
        "scan_limit": "Exact normalized 160-character prefixes of reference responses and judge "
        "justifications; not semantic detection or rights approval. PNG figures "
        "require visual review. PDF text is extracted for scanning.",
    }
    encoded = (json.dumps(manifest, indent=2) + "\n").encode()
    files["EXPORT_MANIFEST.json"] = encoded
    archive = out / "snap-presentation-review.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as dest:
        for rel, content in sorted(files.items()):
            dest.writestr("snap-presentation/" + rel, content)
    (out / "EXPORT_MANIFEST.json").write_bytes(encoded)
    print(
        json.dumps(
            {
                "archive": str(archive),
                "files": len(files),
                "status": manifest["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
