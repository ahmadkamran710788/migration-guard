# claude-migration-guard

A Claude Code plugin marketplace hosting **Migration Guard**, a plugin that stops Claude from
writing database migrations that lock tables, lose data, or cannot be rolled back.

## Install

    /plugin install migration-guard --marketplace ahmadkamran-dimedroppers/claude-migration-guard

Or in two steps:

    /plugin marketplace add ahmadkamran-dimedroppers/claude-migration-guard
    /plugin install migration-guard@claude-migration-guard

## Plugins

| Plugin | What it does |
|---|---|
| [migration-guard](plugins/migration-guard/) | Checks every migration Claude writes for locking, destructive, or irreversible operations and asks before writing. Includes a reviewer agent and a `/migration-guard:migration-review` skill. |

See the [plugin README](plugins/migration-guard/README.md) for the full list of checks, configuration, and tests.
