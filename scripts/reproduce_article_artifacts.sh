#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CORE_OUTPUT="$PROJECT_ROOT/artifacts/reproduction/v3.1-core"
PUBLICATION_OUTPUT="$PROJECT_ROOT/artifacts/reproduction/v3.1-publication"
WORK_DB="$CORE_OUTPUT/snap_poc_v3_1_working.db"

mkdir -p "$CORE_OUTPUT" "$PUBLICATION_OUTPUT"
mkdir -p "$CORE_OUTPUT/cache/matplotlib" "$CORE_OUTPUT/cache/xdg"
cd "$PROJECT_ROOT"
export MPLCONFIGDIR="$CORE_OUTPUT/cache/matplotlib"
export XDG_CACHE_HOME="$CORE_OUTPUT/cache/xdg"

# SoulBenchDB performs schema migrations when it opens a database. All legacy
# CLI analyses therefore run on a disposable byte-for-byte copy, never on the
# tracked evidence database.
cp "$PROJECT_ROOT/data/snap_poc_v3_1.db" "$WORK_DB"

"$PYTHON_BIN" -m pytest -q -p no:cacheprovider
"$PYTHON_BIN" -m src.runner --db-path "$WORK_DB" analyze --stability --output-dir "$CORE_OUTPUT"
"$PYTHON_BIN" -m src.runner --db-path "$WORK_DB" analyze --sensitivity --output-dir "$CORE_OUTPUT"
"$PYTHON_BIN" -m src.runner --db-path "$WORK_DB" analyze --variance-decomposition --output-dir "$CORE_OUTPUT"
"$PYTHON_BIN" -m src.runner --db-path "$WORK_DB" analyze --cross-sp-diagnostic --output-dir "$CORE_OUTPUT"
"$PYTHON_BIN" -m src.runner --db-path "$WORK_DB" decision --reports-dir "$CORE_OUTPUT" --output "$CORE_OUTPUT/decision_report.json"
"$PYTHON_BIN" scripts/reproduce_preliminary.py --project-root "$PROJECT_ROOT" --output-dir "$PUBLICATION_OUTPUT" --seed 20260904 --bootstrap 5000

echo "Reproduction complete:"
echo "  $CORE_OUTPUT"
echo "  $PUBLICATION_OUTPUT"
