# migration-guard

A Claude Code plugin marketplace hosting **Safe Migrations**, a plugin that stops Claude from
writing database migrations that lock tables, lose data, or cannot be rolled back.

## Install

    /plugin install safe-migrations --marketplace ahmadkamran710788/migration-guard

Or in two steps:

    /plugin marketplace add ahmadkamran710788/migration-guard
    /plugin install safe-migrations@ahmadkamran710788

## Plugins

| Plugin | What it does |
|---|---|
| [safe-migrations](plugins/safe-migrations/) | Checks every migration Claude writes for locking, destructive, or irreversible operations and asks before writing. Includes a reviewer agent and a `/safe-migrations:migration-review` skill. |

See the [plugin README](plugins/safe-migrations/README.md) for the full list of checks, configuration, and tests.
