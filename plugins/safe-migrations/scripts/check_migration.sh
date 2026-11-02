#!/usr/bin/env bash
# safe-migrations hook entry point.
# Reads the hook JSON on stdin and runs the bundled checker, check_migration.py,
# with Python 3. The checker prints a permission decision or nothing.
# Makes no network calls and writes no files.
# $1 is only used by the test script to exercise deny/off behaviour.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "safe-migrations: python3 not found on PATH, migration check skipped" >&2
  exit 1
fi
exec python3 "$DIR/check_migration.py" "${1:-ask}"
