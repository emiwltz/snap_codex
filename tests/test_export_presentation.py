from pathlib import Path
import json

import pytest

from scripts.export_presentation import candidates, scan, local_links


def test_allowlist_rejects_raw_data_even_if_explicitly_added(tmp_path):
    manifest = tmp_path / "files.txt"
    for rel in [
        "data/example.db",
        "../outside.md",
        "outputs/reports/cross_sp_diagnostic.json",
        "paper/private/secret.txt",
        ".env",
        "paper/provenance/private.json",
    ]:
        manifest.write_text(rel)
        with pytest.raises(ValueError, match="Forbidden"):
            candidates(tmp_path, manifest)


def test_scan_finds_json_escaped_excerpt_without_printing_it():
    fragment = "A synthetic response with unicode é and a line break. " * 4
    encoded = json.dumps({"response": fragment}, ensure_ascii=True).encode()
    assert scan(
        Path("aggregate.json"), encoded, {" ".join(fragment.split())[:160]}
    ) == ["raw-response-or-judge-excerpt"]
    fake_credential = ("sk-" + "or-v1-" + "z" * 32).encode()
    assert scan(Path("notes.md"), fake_credential, set()) == ["credential-pattern"]


def test_export_links_must_resolve_inside_selected_bundle(tmp_path):
    readme = tmp_path / "README.md"
    target = tmp_path / "data.md"
    target.write_text("Retained locally")
    readme.write_text("[data](data.md)")
    assert local_links([readme], tmp_path)
    assert not local_links([readme, target], tmp_path)


def test_allowlist_rejects_parent_symlink_to_raw_directory(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "raw.csv").write_text("sensitive sample")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "linked").symlink_to(data, target_is_directory=True)
    manifest = tmp_path / "files.txt"
    manifest.write_text("docs/linked/raw.csv")
    with pytest.raises(ValueError, match="linked"):
        candidates(tmp_path, manifest)
