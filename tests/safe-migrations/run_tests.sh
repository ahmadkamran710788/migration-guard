#!/usr/bin/env bash
# Feeds each fixture through the hook as a Write tool call and checks the decision.
set -u
cd "$(dirname "$0")"
PLUGIN=../../plugins/safe-migrations
SCRIPT=$PLUGIN/scripts/check_migration.py
ok=0; bad=0
run() {
  local file="$1" expect="$2" fake_path="$3"
  local out
  out=$(jq -n --arg p "$fake_path" --rawfile c "fixtures/$file" \
        '{tool_name:"Write", tool_input:{file_path:$p, content:$c}}' | python3 "$SCRIPT" ask)
  local got
  if [ -z "$out" ]; then got="allow"; else got=$(echo "$out" | jq -r '.hookSpecificOutput.permissionDecision'); fi
  if [ "$got" = "$expect" ]; then ok=$((ok+1)); echo "PASS $file -> $got"
  else bad=$((bad+1)); echo "FAIL $file -> got $got, expected $expect"; echo "$out"; fi
}
run bad_rails.rb       ask   /app/db/migrate/20250101120000_add_status_to_orders.rb
run good_rails.rb      allow /app/db/migrate/20250101120000_add_status_to_orders.rb
run bad.sql            ask   /app/db/migrations/20250101120000_users_plan.sql
run good.sql           allow /app/db/migrations/20250101120000_users_plan.sql
run bad_django.py      ask   /app/shop/migrations/0008_order_status.py
run not_a_migration.rb allow /app/app/models/user.rb
echo "---"; echo "passed=$ok failed=$bad"
echo; echo "Sample reason for bad.sql:"
jq -n --rawfile c fixtures/bad.sql '{tool_name:"Write", tool_input:{file_path:"/app/db/migrations/1_x.sql", content:$c}}' \
  | python3 "$SCRIPT" ask | jq -r '.hookSpecificOutput.permissionDecisionReason'
[ "$bad" -eq 0 ]

echo; echo "deny mode:"
jq -n --rawfile c fixtures/bad_rails.rb '{tool_name:"Write", tool_input:{file_path:"/app/db/migrate/1_x.rb", content:$c}}' \
  | python3 "$SCRIPT" deny | jq -r '.hookSpecificOutput.permissionDecision'
echo "off mode (expect empty):"
jq -n --rawfile c fixtures/bad_rails.rb '{tool_name:"Write", tool_input:{file_path:"/app/db/migrate/1_x.rb", content:$c}}' \
  | python3 "$SCRIPT" off
