---
name: migration-review
description: Review a database migration for production safety (locks, data loss, rollback, deploy ordering) and get a safe rewrite. Usage: /migration-guard:migration-review [path to migration file, or blank for the newest migration]
argument-hint: "[migration file path]"
---

Review the migration for production safety using the `migration-guard:migration-reviewer` agent.

Target: $ARGUMENTS

If no path was given, find the newest migration file in the project (look in db/migrate,
migrations, prisma/migrations, alembic/versions, database/migrations, supabase/migrations)
and review that one. Tell the user which file you picked.

Launch the agent with the file path and the project root. When it returns, show its full
review to the user. If the verdict is NEEDS CHANGES or DANGEROUS, offer to apply the safe
rewrite, but do not change files until the user says yes.
