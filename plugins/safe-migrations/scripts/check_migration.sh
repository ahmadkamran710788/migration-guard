#!/usr/bin/env bash
# safe-migrations hook entry point.
# Reads the hook JSON on stdin and runs the bundled checker with Python 3.
# Mode comes from the plugin's "mode" option (exported by Claude Code as
# CLAUDE_PLUGIN_OPTION_MODE), or from $1 when run by the test script.
# Defaults to "ask". Makes no network calls and reads nothing else.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-${CLAUDE_PLUGIN_OPTION_MODE:-ask}}"
if ! command -v python3 >/dev/null 2>&1; then
  echo "safe-migrations: python3 not found on PATH, migration check skipped" >&2
  exit 1
fi
exec python3 "$DIR/check_migration.py" "$MODE"
