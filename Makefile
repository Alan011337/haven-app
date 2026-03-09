.PHONY: release-gate-local

release-gate-local:
	./scripts/release-gate-local.sh

.PHONY: release-check

release-check:
	RELEASE_GATE_AUTO_REFRESH_EVIDENCE=0 SKIP_FRONTEND_TYPECHECK=1 SKIP_MOBILE_TYPECHECK=1 ./scripts/release-gate-local.sh

.PHONY: release-gate-local-full

release-gate-local-full:
	RUN_FULL_BACKEND_PYTEST=1 ./scripts/release-gate-local.sh

.PHONY: release-check-full

release-check-full:
	RELEASE_GATE_AUTO_REFRESH_EVIDENCE=0 RUN_FULL_BACKEND_PYTEST=1 ./scripts/release-gate-local.sh

.PHONY: security-gate-fast

security-gate-fast:
	cd backend && API_INVENTORY_AUTO_WRITE=1 SECURITY_GATE_PROFILE=fast ./scripts/security-gate.sh

.PHONY: evidence-clean

evidence-clean:
	./scripts/clean-evidence-noise.sh

.PHONY: alpha-gate-v1

alpha-gate-v1:
	./scripts/alpha-gate-v1-check.sh

.PHONY: alpha-gate-v1-backend

alpha-gate-v1-backend:
	./scripts/alpha-gate-v1-backend-check.sh

.PHONY: alpha-gate-v1-frontend

alpha-gate-v1-frontend:
	./scripts/alpha-gate-v1-frontend-check.sh

.PHONY: alpha-gate-v1-curl

alpha-gate-v1-curl:
	./scripts/alpha-gate-v1-curl-check.sh

.PHONY: env-manifest-refresh

env-manifest-refresh:
	cd backend && PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/generate_env_secret_manifest.py

.PHONY: dev-cleanup-procs

dev-cleanup-procs:
	./scripts/cleanup-dev-processes.sh

.PHONY: dev-cleanup-procs-apply

dev-cleanup-procs-apply:
	./scripts/cleanup-dev-processes.sh --apply

.PHONY: install-git-hooks

install-git-hooks:
	./scripts/install-git-hooks.sh
