from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "deploy-fly-backend.sh"


def _write_fake_flyctl(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

command_name="${1:-}"
shift || true

case "${command_name}" in
  auth)
    exit 0
    ;;
  apps)
    echo "NAME"
    echo "${FAKE_FLY_APP_NAME:-haven-api-prod}"
    exit 0
    ;;
  secrets)
    subcommand="${1:-}"
    shift || true
    case "${subcommand}" in
      list)
        echo "NAME DIGEST STATUS"
        for secret_name in ${FAKE_FLY_SECRETS:-}; do
          echo "${secret_name} digest Deployed"
        done
        exit 0
        ;;
      set)
        printf '%s\\n' "$@" >> "${FAKE_SECRET_SET_LOG}"
        exit 0
        ;;
    esac
    ;;
  deploy|scale|checks)
    if [[ -n "${FAKE_FLY_CALL_LOG:-}" ]]; then
      printf '%s|%s %s\n' "$PWD" "${command_name}" "$*" >> "${FAKE_FLY_CALL_LOG}"
    fi
    exit 0
    ;;
esac

exit 0
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _base_env(fly_bin: Path, config_path: Path, log_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "FLY_BIN",
        "FLY_APP_NAME",
        "FLY_API_TOKEN",
        "FLY_CONFIG_FILE",
        "FLY_DEPLOY_PREFLIGHT_ONLY",
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "SECRET_KEY",
        "CORS_ORIGINS",
        "AI_ROUTER_REDIS_URL",
        "REDIS_URL",
        "ABUSE_GUARD_REDIS_URL",
        "FAKE_FLY_APP_NAME",
        "FAKE_FLY_SECRETS",
        "FAKE_SECRET_SET_LOG",
        "FAKE_FLY_CALL_LOG",
    ):
        env.pop(key, None)
    env.update(
        {
            "FLY_BIN": str(fly_bin),
            "FLY_APP_NAME": "haven-api-prod",
            "FLY_API_TOKEN": "test-token",
            "DATABASE_URL": "postgresql://example",
            "OPENAI_API_KEY": "test-key",
            "SECRET_KEY": "01234567890123456789012345678901",
            "CORS_ORIGINS": '["https://example.com"]',
            "FLY_CONFIG_FILE": str(config_path),
            "FAKE_FLY_APP_NAME": "haven-api-prod",
            "FAKE_SECRET_SET_LOG": str(log_path),
        }
    )
    return env


def test_deploy_script_fails_when_ai_router_redis_secret_missing(tmp_path: Path) -> None:
    fly_bin = tmp_path / "flyctl"
    _write_fake_flyctl(fly_bin)
    config_path = tmp_path / "fly.toml"
    config_path.write_text('[env]\nAI_ROUTER_SHARED_STATE_BACKEND = "redis"\n', encoding="utf-8")
    log_path = tmp_path / "secret-set.log"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env=_base_env(fly_bin, config_path, log_path),
    )

    assert result.returncode == 1
    assert "none of AI_ROUTER_REDIS_URL REDIS_URL ABUSE_GUARD_REDIS_URL are available" in result.stdout


def test_deploy_script_accepts_existing_ai_router_redis_secret_without_plaintext_env(tmp_path: Path) -> None:
    fly_bin = tmp_path / "flyctl"
    _write_fake_flyctl(fly_bin)
    config_path = tmp_path / "fly.toml"
    config_path.write_text('[env]\nAI_ROUTER_SHARED_STATE_BACKEND = "redis"\n', encoding="utf-8")
    log_path = tmp_path / "secret-set.log"
    env = _base_env(fly_bin, config_path, log_path)
    env["FAKE_FLY_SECRETS"] = "AI_ROUTER_REDIS_URL"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ai router redis secret source: existing fly secret (AI_ROUTER_REDIS_URL)" in result.stdout


def test_deploy_script_sets_ai_router_redis_secret_when_env_provided(tmp_path: Path) -> None:
    fly_bin = tmp_path / "flyctl"
    _write_fake_flyctl(fly_bin)
    config_path = tmp_path / "fly.toml"
    config_path.write_text('[env]\nAI_ROUTER_SHARED_STATE_BACKEND = "redis"\n', encoding="utf-8")
    log_path = tmp_path / "secret-set.log"
    env = _base_env(fly_bin, config_path, log_path)
    env["AI_ROUTER_REDIS_URL"] = "redis://redis.internal:6379/0"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ai router redis secret source: deploy env (AI_ROUTER_REDIS_URL)" in result.stdout
    assert "AI_ROUTER_REDIS_URL=redis://redis.internal:6379/0" in log_path.read_text(encoding="utf-8")


def test_deploy_script_accepts_abuse_guard_secret_as_ai_router_shared_state_fallback(tmp_path: Path) -> None:
    fly_bin = tmp_path / "flyctl"
    _write_fake_flyctl(fly_bin)
    config_path = tmp_path / "fly.toml"
    config_path.write_text('[env]\nAI_ROUTER_SHARED_STATE_BACKEND = "redis"\n', encoding="utf-8")
    log_path = tmp_path / "secret-set.log"
    env = _base_env(fly_bin, config_path, log_path)
    env["FAKE_FLY_SECRETS"] = "ABUSE_GUARD_REDIS_URL"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ai router redis secret source: existing fly secret (ABUSE_GUARD_REDIS_URL)" in result.stdout


def test_deploy_script_fails_when_abuse_guard_redis_secret_missing(tmp_path: Path) -> None:
    fly_bin = tmp_path / "flyctl"
    _write_fake_flyctl(fly_bin)
    config_path = tmp_path / "fly.toml"
    config_path.write_text('[env]\nABUSE_GUARD_STORE_BACKEND = "redis"\n', encoding="utf-8")
    log_path = tmp_path / "secret-set.log"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env=_base_env(fly_bin, config_path, log_path),
    )

    assert result.returncode == 1
    assert "ABUSE_GUARD_REDIS_URL is missing" in result.stdout


def test_deploy_script_accepts_existing_abuse_guard_redis_secret_without_plaintext_env(tmp_path: Path) -> None:
    fly_bin = tmp_path / "flyctl"
    _write_fake_flyctl(fly_bin)
    config_path = tmp_path / "fly.toml"
    config_path.write_text('[env]\nABUSE_GUARD_STORE_BACKEND = "redis"\n', encoding="utf-8")
    log_path = tmp_path / "secret-set.log"
    env = _base_env(fly_bin, config_path, log_path)
    env["FAKE_FLY_SECRETS"] = "ABUSE_GUARD_REDIS_URL"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "abuse guard redis secret source: existing fly secret (ABUSE_GUARD_REDIS_URL)" in result.stdout


def test_deploy_script_sets_abuse_guard_redis_secret_when_env_provided(tmp_path: Path) -> None:
    fly_bin = tmp_path / "flyctl"
    _write_fake_flyctl(fly_bin)
    config_path = tmp_path / "fly.toml"
    config_path.write_text('[env]\nABUSE_GUARD_STORE_BACKEND = "redis"\n', encoding="utf-8")
    log_path = tmp_path / "secret-set.log"
    env = _base_env(fly_bin, config_path, log_path)
    env["ABUSE_GUARD_REDIS_URL"] = "redis://redis.internal:6379/1"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "abuse guard redis secret source: deploy env (ABUSE_GUARD_REDIS_URL)" in result.stdout
    assert "ABUSE_GUARD_REDIS_URL=redis://redis.internal:6379/1" in log_path.read_text(encoding="utf-8")


def test_deploy_script_preflight_only_exits_before_secret_set_and_deploy(tmp_path: Path) -> None:
    fly_bin = tmp_path / "flyctl"
    _write_fake_flyctl(fly_bin)
    config_path = tmp_path / "fly.toml"
    config_path.write_text(
        '[env]\nAI_ROUTER_SHARED_STATE_BACKEND = "redis"\nABUSE_GUARD_STORE_BACKEND = "redis"\n',
        encoding="utf-8",
    )
    log_path = tmp_path / "secret-set.log"
    env = _base_env(fly_bin, config_path, log_path)
    env["AI_ROUTER_REDIS_URL"] = "redis://redis.internal:6379/0"
    env["ABUSE_GUARD_REDIS_URL"] = "redis://redis.internal:6379/1"
    env["FLY_DEPLOY_PREFLIGHT_ONLY"] = "1"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[fly-deploy] preflight-only: pass" in result.stdout
    assert not log_path.exists()


def test_deploy_script_uses_explicit_flyctl_home_for_auth_and_preflight(tmp_path: Path) -> None:
    fly_bin = tmp_path / "flyctl"
    _write_fake_flyctl(fly_bin)
    config_path = tmp_path / "fly.toml"
    config_path.write_text('[env]\nAI_ROUTER_SHARED_STATE_BACKEND = "redis"\n', encoding="utf-8")
    log_path = tmp_path / "secret-set.log"
    fly_home = tmp_path / "fly-home"
    env = _base_env(fly_bin, config_path, log_path)
    env["AI_ROUTER_REDIS_URL"] = "redis://redis.internal:6379/0"
    env["FLYCTL_HOME"] = str(fly_home)
    env["FLY_DEPLOY_PREFLIGHT_ONLY"] = "1"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"[fly-deploy] flyctl home: {fly_home}" in result.stdout


def test_deploy_script_runs_fly_deploy_from_backend_directory(tmp_path: Path) -> None:
    fly_bin = tmp_path / "flyctl"
    _write_fake_flyctl(fly_bin)
    config_path = tmp_path / "fly.toml"
    config_path.write_text('[env]\n', encoding="utf-8")
    log_path = tmp_path / "secret-set.log"
    call_log_path = tmp_path / "fly-call.log"
    env = _base_env(fly_bin, config_path, log_path)
    env["FAKE_FLY_CALL_LOG"] = str(call_log_path)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    call_log = call_log_path.read_text(encoding="utf-8")
    assert f"{BACKEND_ROOT}|deploy " in call_log
