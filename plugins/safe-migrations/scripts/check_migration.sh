#!/usr/bin/env bash
# safe-migrations hook entry point: runs the bundled checker with Python 3.
# Hook JSON arrives on stdin; the checker prints a permission decision or nothing.
# No network calls, no files written.
if ! command -v python3 >/dev/null 2>&1; then
  echo "safe-migrations: python3 not found on PATH, migration check skipped" >&2
  exit 1
fi
exec python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_migration.py"
