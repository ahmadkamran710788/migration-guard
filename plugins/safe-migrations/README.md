# Safe Migrations

A Claude Code plugin that stops risky database migrations before they are written.

Most production outages caused by migrations come from a handful of patterns: an index built
without `CONCURRENTLY`, a `NOT NULL` column with no default, a rename while old code is still
running, a backfill inside the schema transaction, a drop with no way back. Reviewers miss them
because they look like normal code. This plugin catches them at the moment Claude writes the file.

## What it does

- **Hook (automatic).** Every time Claude writes or edits a file that looks like a migration
  (Rails, Django, Alembic, Prisma, Knex, Drizzle, Laravel, dbmate, Flyway, raw SQL), the file is
  checked for locking, destructive, and irreversible operations. If anything is found you get a
  permission prompt listing each issue, its line, and the fix. Approve to write it anyway, or deny
  and Claude rewrites it using the fixes. Clean migrations are written without any prompt.
- **Agent `migration-reviewer`.** A deep review that states the lock each statement takes, checks
  deploy ordering and rollback, and produces a safe multi-step rewrite in your framework's style.
- **Skill `/safe-migrations:migration-review [file]`.** Runs the agent on a file, or on the newest
  migration if you give no path.

## Checks performed by the hook

| Category | Examples caught |
|---|---|
| Blocking index builds | `CREATE INDEX` without `CONCURRENTLY`, `add_index` without `algorithm: :concurrently`, `migrations.AddIndex`, `op.create_index` |
| NOT NULL without default | `ADD COLUMN ... NOT NULL`, `add_column ... null: false` |
| Table rewrites | `ALTER COLUMN TYPE`, `change_column`, `MODIFY COLUMN` |
| Renames | `RENAME COLUMN`, `rename_column`, `RenameField`, `RenameModel` |
| Destructive | `DROP TABLE`, `DROP COLUMN`, `TRUNCATE`, `remove_column`, `DeleteModel` |
| Unvalidated constraints | `ADD CONSTRAINT ... FOREIGN KEY/CHECK` without `NOT VALID`, `add_foreign_key` without `validate: false`, `change_column_null` |
| Backfills in migrations | `UPDATE ... SET` without batching, `update_all`, `RunPython` without `reverse_code` |
| Heavy locks | `LOCK TABLE`, `VACUUM FULL`, `CLUSTER`, blocking `REINDEX` |
| Rails specifics | `algorithm: :concurrently` without `disable_ddl_transaction!` |
| Missing rollback | Alembic without `downgrade()`, Knex/TS without `down`, dbmate SQL without `migrate:down` |

## Install

From the marketplace (Claude Code 2.1.275 or later, one step):

    /plugin install safe-migrations --marketplace ahmadkamran710788/migration-guard

Or in two steps:

    /plugin marketplace add ahmadkamran710788/migration-guard
    /plugin install safe-migrations@ahmadkamran710788

Try it locally without installing:

    claude --plugin-dir ./plugins/safe-migrations

## Turn it off

Disable the plugin in `/plugin` when you do not want the check, for example while working on a
throwaway database. There is nothing else to configure.

## What it runs

One local script, `scripts/check_migration.sh`, which starts `scripts/check_migration.py` with
Python 3. It reads the hook input from Claude Code on standard input, scans the migration text with
regular expressions, and prints a permission decision. It makes no network requests, and writes nothing to disk. If Python 3 is missing it
reports that once and lets the write proceed.

## Test

    bash plugins/safe-migrations/tests/run_tests.sh

Feeds sample migrations through the hook and checks the decision for each.

## Publish

This repo is laid out as a marketplace: `.claude-plugin/marketplace.json` at the root and the
plugin under `plugins/safe-migrations/`. It is hosted at
https://github.com/ahmadkamran710788/migration-guard.

To release a change: bump `version` in `.claude-plugin/plugin.json`, run
`claude plugin validate plugins/safe-migrations` and `claude plugin validate .` from the repo
root, commit, and push. Users get the update with `/plugin update safe-migrations`.

## Requirements

Python 3 and bash on the PATH. macOS and Linux have both; on Windows install Git Bash and Python 3.

## License

MIT
