# Migration Guard

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
  and Claude rewrites it using the fixes.
- **Agent `migration-reviewer`.** A deep review that states the lock each statement takes, checks
  deploy ordering and rollback, and produces a safe multi-step rewrite in your framework's style.
- **Skill `/migration-guard:migration-review [file]`.** Runs the agent on a file, or on the newest
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

    /plugin install migration-guard --marketplace ahmadkamran-dimedroppers/claude-migration-guard

Or in two steps:

    /plugin marketplace add ahmadkamran-dimedroppers/claude-migration-guard
    /plugin install migration-guard@claude-migration-guard

Try it locally without installing:

    claude --plugin-dir ./migration-guard

## Configure

Set an environment variable before starting Claude Code:

| `MIGRATION_GUARD_MODE` | Behaviour |
|---|---|
| `ask` (default) | Prompt you with the issues and let you decide |
| `deny` | Block the write and send the issues to Claude so it rewrites the file |
| `off` | Disable the hook |

## Test

    bash migration-guard/tests/run_tests.sh

Feeds sample migrations through the hook and checks the decision for each.

## Publish

This repo is laid out as a marketplace: `.claude-plugin/marketplace.json` at the root and the
plugin under `plugins/migration-guard/`. It is hosted at
https://github.com/ahmadkamran-dimedroppers/claude-migration-guard.

To release a change: bump `version` in `.claude-plugin/plugin.json`, run
`claude plugin validate plugins/migration-guard` and `claude plugin validate .` from the repo
root, commit, and push. Users get the update with `/plugin update migration-guard`.

## Requirements

Python 3 on the PATH (macOS and most Linux distributions have it).

## License

MIT
