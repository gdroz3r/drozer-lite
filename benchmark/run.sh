#!/usr/bin/env bash
# drozer-lite benchmark harness — generic driver.
#
# Usage: benchmark/run.sh <benchmark-name>
# Supported: forefy-autonomous-audit
#
# The harness fetches the benchmark corpus at a pinned commit, prepares the run
# directory, and describes how to score. drozer-lite itself runs inside Claude
# Code and writes output.json; this script brackets that work.

set -euo pipefail

BENCH="${1:-}"
if [[ -z "$BENCH" ]]; then
  echo "Usage: $0 <benchmark-name>"
  echo "  Supported: forefy-autonomous-audit"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASELINE="$REPO_ROOT/benchmark/baseline.json"

case "$BENCH" in
  forefy-autonomous-audit)
    REPO_URL="https://github.com/forefy/benchmarks"
    PINNED_COMMIT="d27d927bc0c3d083500200c39068b809b12bf881"
    CORPUS_PATH="autonomous-audit/corpus/public"
    PROGRAM_PATH="autonomous-audit/program.md"
    SCORER_PATH="autonomous-audit/scorer.py"
    EXPECTED_PATH="autonomous-audit/expected.json"
    OUTPUT_REL="autonomous-audit/output.json"
    ;;
  *)
    echo "Unknown benchmark: $BENCH"
    exit 1
    ;;
esac

RUN_DIR="$REPO_ROOT/.benchmark-runs/${BENCH}-$(date +%s)"
mkdir -p "$RUN_DIR"
cd "$RUN_DIR"

echo "[1/4] Cloning $BENCH at pinned commit..."
git clone --filter=blob:none --sparse "$REPO_URL" . -q
git checkout "$PINNED_COMMIT" 2>&1 | tail -1
git sparse-checkout set --skip-checks "$CORPUS_PATH" "$PROGRAM_PATH" "$SCORER_PATH" "$EXPECTED_PATH" 2>/dev/null || true

echo "[2/4] Run directory: $RUN_DIR"
echo
echo "[3/4] drozer-lite must now run against each case folder in $CORPUS_PATH"
echo "      and write $OUTPUT_REL in the schema described in $PROGRAM_PATH."
echo
echo "[4/4] Once output.json is written, score with:"
echo "      cd $RUN_DIR/$(dirname "$OUTPUT_REL")"
echo "      python3 $(basename "$SCORER_PATH") output.json expected.json"
echo
echo "Baseline for $BENCH: see $BASELINE"
echo "Any score below baseline is a regression and must be justified before merge."
