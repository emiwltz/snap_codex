import pytest

from scripts.local_paths import fresh_directory


def test_output_guard_preserves_evidence_and_rejects_symlink_escape(tmp_path):
    evidence = tmp_path / "data"
    evidence.mkdir()
    original = evidence / "reference.db"
    original.write_bytes(b"retained evidence")
    runs = tmp_path / "artifacts/runs"
    runs.mkdir(parents=True)
    (runs / "linked").symlink_to(evidence, target_is_directory=True)
    for path in [evidence, runs, runs / "linked/new", tmp_path / "outside"]:
        with pytest.raises(ValueError):
            fresh_directory(path, tmp_path, ("artifacts/runs",))
    assert original.read_bytes() == b"retained evidence"
    assert not (evidence / "new").exists()


def test_output_guard_requires_new_run(tmp_path):
    target = tmp_path / "artifacts/runs/review"
    assert fresh_directory(target, tmp_path, ("artifacts/runs",)) == target
    marker = target / "completed.json"
    marker.write_text("original")
    with pytest.raises(ValueError, match="already exists"):
        fresh_directory(target, tmp_path, ("artifacts/runs",))
    assert marker.read_text() == "original"
