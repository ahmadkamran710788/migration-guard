#!/usr/bin/env python3
"""
migration-guard: PreToolUse hook that inspects database migration files before
Claude writes them and flags operations that lock tables, rewrite data, or
cannot be rolled back.

Reads the hook JSON from stdin. If the file is not a migration, exits 0 silently.
If risky operations are found, asks the user for permission with a reason that
lists every issue and how to fix it.

Environment:
  MIGRATION_GUARD_MODE   ask (default) | deny | off
"""
import json
import os
import re
import sys

MIGRATION_PATH_HINTS = (
    "/migrations/", "/migrate/", "/db/migrate/", "/prisma/migrations/",
    "/alembic/versions/", "/database/migrations/", "/knex/", "/drizzle/",
    "/supabase/migrations/", "/flyway/", "/liquibase/", "/sql/migrations/",
)
MIGRATION_NAME_RE = re.compile(r"(^|/)(\d{4,}[_-].*|V\d+__.*|.*migration.*)\.(sql|rb|py|js|ts|go|php|cs)$", re.I)

# Each check: (id, severity, regex, message, fix)
# severity: "danger" = data loss or guaranteed outage, "warn" = lock or long transaction risk
CHECKS = [
    # ---- Index creation / removal without CONCURRENTLY (PostgreSQL) ----
    ("index-blocking", "warn",
     re.compile(r"\bCREATE\s+(UNIQUE\s+)?INDEX\b(?![^;\n]*\bCONCURRENTLY\b)", re.I),
     "CREATE INDEX without CONCURRENTLY blocks writes to the table for the whole build.",
     "Use CREATE INDEX CONCURRENTLY (outside a transaction)."),
    ("index-blocking", "warn",
     re.compile(r"\bDROP\s+INDEX\b(?![^;\n]*\bCONCURRENTLY\b)", re.I),
     "DROP INDEX without CONCURRENTLY takes an exclusive lock.",
     "Use DROP INDEX CONCURRENTLY."),
    ("index-blocking", "warn",
     re.compile(r"\badd_index\b(?![^\n]*algorithm:\s*:concurrently)", re.I),
     "add_index without algorithm: :concurrently blocks writes (PostgreSQL).",
     "add_index ..., algorithm: :concurrently and add disable_ddl_transaction! at the top."),
    ("index-blocking", "warn",
     re.compile(r"\badd_reference\b[^\n]*index:\s*true(?![^\n]*concurrently)", re.I),
     "add_reference with index: true builds the index with a blocking lock.",
     "Use index: { algorithm: :concurrently } or add the index in a separate concurrent migration."),
    ("index-blocking", "warn",
     re.compile(r"\bmigrations\.AddIndex\(", re.I),
     "migrations.AddIndex builds the index inside a transaction with a blocking lock.",
     "Use django.contrib.postgres.operations.AddIndexConcurrently with atomic = False."),
    ("index-blocking", "warn",
     re.compile(r"\bop\.create_index\((?![^\n]*postgresql_concurrently\s*=\s*True)", re.I),
     "op.create_index without postgresql_concurrently=True blocks writes.",
     "Pass postgresql_concurrently=True and run with op.get_context().autocommit_block()."),

    # ---- NOT NULL column added without default ----
    ("not-null-no-default", "danger",
     re.compile(r"\bADD\s+(COLUMN\s+)?\w+\s+[\w\(\),]+\s+NOT\s+NULL\b(?![^;\n]*\bDEFAULT\b)", re.I),
     "Adding a NOT NULL column without a DEFAULT fails on any table that already has rows.",
     "Add the column as nullable, backfill in batches, then add the NOT NULL constraint (NOT VALID, then VALIDATE)."),
    ("not-null-no-default", "danger",
     re.compile(r"\badd_column\b[^\n]*null:\s*false(?![^\n]*default:)", re.I),
     "add_column with null: false and no default fails on populated tables.",
     "Add nullable first, backfill, then change_column_null in a later migration."),

    # ---- Column type changes (full table rewrite) ----
    ("type-change", "warn",
     re.compile(r"\bALTER\s+(COLUMN\s+)?\w+\s+(SET\s+DATA\s+)?TYPE\b", re.I),
     "ALTER COLUMN TYPE rewrites the whole table under an ACCESS EXCLUSIVE lock.",
     "Add a new column, dual-write, backfill, then swap. Some widenings (varchar(n) to text) are safe."),
    ("type-change", "warn",
     re.compile(r"\bchange_column\b(?!_null|_default|_comment)", re.I),
     "change_column rewrites the table and is not reversible in a change block.",
     "Use up/down methods, or add a new column and migrate data."),
    ("type-change", "warn",
     re.compile(r"\bMODIFY\s+(COLUMN\s+)?\w+", re.I),
     "MODIFY COLUMN (MySQL) copies the table unless the change is in-place eligible.",
     "Use ALGORITHM=INPLACE, LOCK=NONE where supported, or an online schema tool (gh-ost, pt-osc)."),

    # ---- Renames (break the running app during deploy) ----
    ("rename", "danger",
     re.compile(r"\bRENAME\s+(COLUMN|TO)\b|\brename_column\b|\brename_table\b|\bRenameField\(|\bRenameModel\(|\bop\.alter_column\([^\n]*new_column_name", re.I),
     "Renaming a column or table breaks every running instance of the old code until the deploy finishes.",
     "Add the new name, dual-write, backfill, switch reads, then drop the old name in a later release."),

    # ---- Destructive drops ----
    ("drop", "danger",
     re.compile(r"\bDROP\s+TABLE\b|\bdrop_table\b|\bDeleteModel\(|\bop\.drop_table\(|\bdropTable\(", re.I),
     "DROP TABLE is irreversible and deletes data immediately.",
     "Rename or archive the table first and drop it in a later release after a backup is confirmed."),
    ("drop", "danger",
     re.compile(r"\bDROP\s+COLUMN\b|\bremove_column\b|\bRemoveField\(|\bop\.drop_column\(|\bdropColumn\(", re.I),
     "DROP COLUMN loses data and breaks old code still selecting that column (ORMs cache columns).",
     "Mark the column ignored in the model first, deploy, then drop it in the next release."),
    ("drop", "danger",
     re.compile(r"\bTRUNCATE\b", re.I),
     "TRUNCATE deletes all rows and cannot be undone.",
     "Do data clean-up outside schema migrations, with a backup."),

    # ---- Constraints without NOT VALID ----
    ("constraint-validate", "warn",
     re.compile(r"\bADD\s+CONSTRAINT\b[^;]*\b(FOREIGN\s+KEY|CHECK)\b(?![^;]*\bNOT\s+VALID\b)", re.I | re.S),
     "ADD CONSTRAINT scans the whole table and holds a lock while it validates.",
     "Add with NOT VALID, then VALIDATE CONSTRAINT in a separate statement (SHARE UPDATE EXCLUSIVE only)."),
    ("constraint-validate", "warn",
     re.compile(r"\badd_foreign_key\b(?![^\n]*validate:\s*false)", re.I),
     "add_foreign_key validates existing rows under a lock on both tables.",
     "add_foreign_key ..., validate: false, then validate_foreign_key in a later migration."),
    ("constraint-validate", "warn",
     re.compile(r"\badd_check_constraint\b(?![^\n]*validate:\s*false)", re.I),
     "add_check_constraint scans the table under a lock.",
     "Pass validate: false, then validate_check_constraint later."),
    ("constraint-validate", "warn",
     re.compile(r"\bchange_column_null\b[^\n]*,\s*false", re.I),
     "change_column_null to false scans the whole table under ACCESS EXCLUSIVE.",
     "Add a CHECK (col IS NOT NULL) NOT VALID, validate it, then set NOT NULL (fast on PG 12+)."),

    # ---- Data backfills inside schema migrations ----
    ("backfill", "warn",
     re.compile(r"^\s*UPDATE\s+\w+\s+SET\b(?![^;]*\bLIMIT\b)", re.I | re.M),
     "An unbatched UPDATE in a migration runs in one long transaction and locks every touched row.",
     "Backfill in batches from a job or script, outside the schema migration."),
    ("backfill", "warn",
     re.compile(r"\b(update_all|find_each|\.update\(|execute\s*\(?\s*['\"]UPDATE)\b", re.I),
     "Data backfill inside a schema migration holds the migration transaction open.",
     "Move the backfill to a separate data migration or background job that batches."),
    ("backfill", "warn",
     re.compile(r"\bRunPython\((?![^\n]*reverse_code)", re.I),
     "RunPython without reverse_code makes the migration irreversible.",
     "Pass reverse_code=migrations.RunPython.noop or a real reverse function."),

    # ---- Heavy locks ----
    ("heavy-lock", "danger",
     re.compile(r"\bLOCK\s+TABLE\b|\bVACUUM\s+FULL\b|\bCLUSTER\s+\w+|\bREINDEX\b(?![^;\n]*CONCURRENTLY)", re.I),
     "Explicit table lock, VACUUM FULL, CLUSTER or blocking REINDEX stops all access to the table.",
     "Run these in a maintenance window, or use REINDEX CONCURRENTLY."),
]

RAILS_CONCURRENT_RE = re.compile(r"algorithm:\s*:concurrently", re.I)
RAILS_DISABLE_DDL_RE = re.compile(r"disable_ddl_transaction!", re.I)
ALEMBIC_RE = re.compile(r"\bop\.\w+\(")
ALEMBIC_DOWN_RE = re.compile(r"def\s+downgrade\s*\(")
KNEX_UP_RE = re.compile(r"(exports\.up|export\s+(async\s+)?function\s+up|up\s*[:=]\s*(async\s*)?\()")
KNEX_DOWN_RE = re.compile(r"(exports\.down|export\s+(async\s+)?function\s+down|down\s*[:=]\s*(async\s*)?\()")
DBMATE_UP_RE = re.compile(r"--\s*migrate:up", re.I)
DBMATE_DOWN_RE = re.compile(r"--\s*migrate:down", re.I)


def is_migration(path: str) -> bool:
    p = path.replace("\\", "/")
    lower = p.lower()
    if any(h in lower for h in MIGRATION_PATH_HINTS):
        return True
    return bool(MIGRATION_NAME_RE.search(p))


def collect_content(tool_input: dict) -> str:
    if "content" in tool_input and isinstance(tool_input["content"], str):
        return tool_input["content"]
    if "new_string" in tool_input and isinstance(tool_input["new_string"], str):
        return tool_input["new_string"]
    if "edits" in tool_input and isinstance(tool_input["edits"], list):
        return "\n".join(e.get("new_string", "") for e in tool_input["edits"] if isinstance(e, dict))
    return ""


def strip_comments(text: str) -> str:
    text = re.sub(r"--[^\n]*", "", text)          # SQL line comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)  # block comments
    text = re.sub(r"(?m)^\s*#[^\n]*", "", text)      # ruby/python comments
    text = re.sub(r"(?m)//[^\n]*", "", text)         # js comments
    return text


def analyze(content: str, path: str) -> list:
    text = strip_comments(content)
    issues = []
    seen = set()
    for cid, sev, rx, msg, fix in CHECKS:
        m = rx.search(text)
        if m:
            line = text.count("\n", 0, m.start()) + 1
            key = (cid, msg)
            if key in seen:
                continue
            seen.add(key)
            issues.append({"id": cid, "severity": sev, "line": line, "message": msg, "fix": fix})

    # Rails: concurrently used but DDL transaction not disabled
    if RAILS_CONCURRENT_RE.search(text) and not RAILS_DISABLE_DDL_RE.search(text):
        issues.append({"id": "rails-ddl-transaction", "severity": "danger", "line": 1,
                       "message": "algorithm: :concurrently fails inside a transaction; disable_ddl_transaction! is missing.",
                       "fix": "Add disable_ddl_transaction! at the top of the migration class."})

    # Missing down / reverse paths
    lower = path.lower()
    if lower.endswith(".py") and ALEMBIC_RE.search(text) and not ALEMBIC_DOWN_RE.search(text):
        issues.append({"id": "no-down", "severity": "warn", "line": 1,
                       "message": "Alembic migration has no downgrade().",
                       "fix": "Add a downgrade() that reverses every op."})
    if lower.endswith((".js", ".ts")) and KNEX_UP_RE.search(text) and not KNEX_DOWN_RE.search(text):
        issues.append({"id": "no-down", "severity": "warn", "line": 1,
                       "message": "Migration defines up but no down.",
                       "fix": "Add a down migration that reverses the change."})
    if lower.endswith(".sql") and DBMATE_UP_RE.search(text) and not DBMATE_DOWN_RE.search(text):
        issues.append({"id": "no-down", "severity": "warn", "line": 1,
                       "message": "SQL migration has migrate:up but no migrate:down.",
                       "fix": "Add a -- migrate:down section."})
    return issues


def format_reason(path: str, issues: list, mode: str = "ask") -> str:
    dangers = [i for i in issues if i["severity"] == "danger"]
    warns = [i for i in issues if i["severity"] == "warn"]
    lines = [f"migration-guard found {len(issues)} risk(s) in {os.path.basename(path)}:"]
    for i in dangers:
        lines.append(f"  [DANGER] line {i['line']}: {i['message']}\n           Fix: {i['fix']}")
    for i in warns:
        lines.append(f"  [WARN]   line {i['line']}: {i['message']}\n           Fix: {i['fix']}")
    if mode == "deny":
        lines.append("Rewrite the migration using the fixes above (expand/contract, concurrent index, NOT VALID + VALIDATE).")
    else:
        lines.append("Approve to write it anyway, or deny and let Claude rewrite it using the fixes above.")
    return "\n".join(lines)


def main() -> int:
    mode = os.environ.get("MIGRATION_GUARD_MODE", "ask").lower()
    if mode == "off":
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path or not is_migration(path):
        return 0
    content = collect_content(tool_input)
    if not content.strip():
        return 0
    issues = analyze(content, path)
    if not issues:
        return 0
    decision = "deny" if mode == "deny" else "ask"
    reason = format_reason(path, issues, decision)
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
