#!/usr/bin/env bash
# run-real-benchmark.sh — execute drozer-lite against the bundled fixture corpus
# using a real Anthropic API key.
#
# WARNING: this WILL spend money. Each fixture case costs ~2 LLM calls
# (one vulnerable, one clean). With 11 fixtures that is ~22 calls per run.
# At Opus 4.5 pricing this is roughly $1-3 per run depending on cache hits.
#
# Prerequisites:
#   * pip install -e .
#   * export ANTHROPIC_API_KEY=sk-ant-...
#
# Usage:
#   ./scripts/run-real-benchmark.sh                 # default model
#   ./scripts/run-real-benchmark.sh -o report.md    # write to file
#   MODEL=claude-opus-4-5 ./scripts/run-real-benchmark.sh
#
# After running, copy the resulting Markdown report into BENCHMARKS.md
# and commit the snapshot so the README links to a real number.

set -euo pipefail

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set." >&2
  exit 2
fi

MODEL="${MODEL:-claude-opus-4-5}"
OUTPUT_ARG=()
if [[ $# -gt 0 ]]; then
  OUTPUT_ARG=("$@")
fi

drozer-lite benchmark --model "$MODEL" "${OUTPUT_ARG[@]}"
