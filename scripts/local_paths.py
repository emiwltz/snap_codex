"""Validate new local output directories without touching retained evidence."""

from pathlib import Path


def fresh_directory(path: Path, root: Path, allowed: tuple[str, ...]) -> Path:
    """Create a new directory below an explicitly disposable output tree.

    Resolve symlinks first, and reject existing directories, including empty ones.
    This guards against accidental reference replacement, not a malicious process
    concurrently changing the filesystem.
    """
    root = root.resolve()
    target = path.resolve()
    if not any(
        target.is_relative_to(root / prefix) and target != root / prefix
        for prefix in allowed
    ):
        raise ValueError(f"Choose a new subdirectory below: {', '.join(allowed)}")
    if target.exists():
        raise ValueError("Output directory already exists; choose a new run name")
    target.mkdir(parents=True, exist_ok=False)
    return target
