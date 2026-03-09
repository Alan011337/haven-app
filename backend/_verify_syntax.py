#!/usr/bin/env python3
import ast
import sys
files = [
    "app/main.py",
    "app/core/socket_manager.py",
    "app/core/config.py",
    "app/api/deps.py",
    "app/api/journals.py",
    "app/api/routers/cards.py",
    "app/api/routers/users.py",
    "app/api/routers/admin.py",
    "app/services/sre_tier_policy.py",
    "app/services/ws_runtime_metrics.py",
    "app/services/cuj_event_emitter.py",
    "app/services/cuj_sli_runtime.py",
    "app/services/entitlement_runtime.py",
    "app/services/degradation_runtime.py",
    "app/services/lifecycle_solo_mode.py",
    "scripts/check_admin_least_privilege.py",
    "scripts/check_billing_edge_policy_contract.py",
    "scripts/check_store_enforcement_hooks_contract.py",
    "scripts/check_canary_rollout_contract.py",
    "scripts/check_sre_tier_policy_contract.py",
    "scripts/run_unit_economics_report.py",
    "tests/test_admin_least_privilege.py",
    "tests/test_billing_edge_policy_contract.py",
    "tests/test_store_enforcement_hooks_contract.py",
]
ok = fail = 0
for f in files:
    try:
        ast.parse(open(f).read())
        print(f"  OK  {f}")
        ok += 1
    except SyntaxError as e:
        print(f"FAIL  {f}: {e}")
        fail += 1
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
