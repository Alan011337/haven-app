#!/usr/bin/env python3
"""Fetch latest daily AI quality snapshot evidence from GitHub Actions artifacts."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from typing import Any, Callable
from urllib import error, parse, request
import zipfile
import os

GITHUB_REPOSITORY_ENV_KEY = "GITHUB_REPOSITORY"
GITHUB_TOKEN_ENV_KEY = "GITHUB_TOKEN"

DEFAULT_WORKFLOW_FILE = ".github/workflows/ai-quality-snapshot.yml"
DEFAULT_BRANCH = "main"
DEFAULT_ARTIFACT_NAME = "ai-quality-snapshot"
DEFAULT_ARTIFACT_FILE = "docs/security/evidence/ai-quality-snapshot-latest.json"
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_OUTPUT_PATH = "/tmp/ai-quality-snapshot-latest.json"

SKIPPABLE_FAILURE_REASONS = frozenset(
    {
        "missing_github_repository",
        "missing_github_token",
        "workflow_run_not_found",
        "artifact_not_found",
        "artifact_file_not_found",
    }
)


class FetchEvidenceError(RuntimeError):
    def __init__(self, reason: str, detail: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def _parse_positive_float(raw: str | None, *, default: float) -> float:
    if raw is None or str(raw).strip() == "":
        return default
    value = float(str(raw).strip())
    if value <= 0:
        raise ValueError("value must be greater than 0")
    return value


def _validate_repo(raw_repo: str) -> str:
    repo = raw_repo.strip()
    if not repo:
        raise FetchEvidenceError("missing_github_repository")
    if "/" not in repo:
        raise FetchEvidenceError("invalid_github_repository")
    owner, name = repo.split("/", 1)
    if not owner or not name:
        raise FetchEvidenceError("invalid_github_repository")
    return repo


def _validate_token(raw_token: str) -> str:
    token = raw_token.strip()
    if not token:
        raise FetchEvidenceError("missing_github_token")
    return token


def _github_headers(token: str, *, accept: str = "application/vnd.github+json") -> dict[str, str]:
    return {
        "Accept": accept,
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "haven-ai-quality-evidence-fetcher",
    }


def _http_get_json(*, url: str, token: str, timeout_seconds: float) -> dict[str, Any]:
    req = request.Request(
        url,
        headers=_github_headers(token),
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", response.getcode()))
            text = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raise FetchEvidenceError("github_http_error", detail=f"http_{exc.code}") from exc
    except error.URLError as exc:
        raise FetchEvidenceError("github_request_error", detail=str(exc.reason)) from exc

    if status_code >= 400:
        raise FetchEvidenceError("github_http_error", detail=f"http_{status_code}")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FetchEvidenceError("invalid_github_response") from exc
    if not isinstance(payload, dict):
        raise FetchEvidenceError("invalid_github_response")
    return payload


def _http_get_bytes(*, url: str, token: str, timeout_seconds: float) -> bytes:
    req = request.Request(
        url,
        headers=_github_headers(token, accept="application/octet-stream"),
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", response.getcode()))
            blob = response.read()
    except error.HTTPError as exc:
        raise FetchEvidenceError("artifact_download_error", detail=f"http_{exc.code}") from exc
    except error.URLError as exc:
        raise FetchEvidenceError("artifact_download_error", detail=str(exc.reason)) from exc

    if status_code >= 400:
        raise FetchEvidenceError("artifact_download_error", detail=f"http_{status_code}")
    return blob


def _resolve_workflow_run_id(payload: dict[str, Any]) -> int:
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        raise FetchEvidenceError("invalid_workflow_runs_payload")
    for item in runs:
        if not isinstance(item, dict):
            continue
        run_id = item.get("id")
        if isinstance(run_id, int):
            return run_id
        if isinstance(run_id, str) and run_id.isdigit():
            return int(run_id)
    raise FetchEvidenceError("workflow_run_not_found")


def _resolve_artifact(payload: dict[str, Any], *, artifact_name: str) -> tuple[int, str]:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise FetchEvidenceError("invalid_artifacts_payload")

    for item in artifacts:
        if not isinstance(item, dict):
            continue
        if str(item.get("name") or "") != artifact_name:
            continue
        if bool(item.get("expired", False)):
            continue
        artifact_id = item.get("id")
        archive_download_url = item.get("archive_download_url")
        if isinstance(artifact_id, str) and artifact_id.isdigit():
            artifact_id = int(artifact_id)
        if not isinstance(artifact_id, int) or artifact_id <= 0:
            continue
        if not isinstance(archive_download_url, str) or not archive_download_url.strip():
            continue
        return artifact_id, archive_download_url.strip()

    raise FetchEvidenceError("artifact_not_found")


def _extract_artifact_file(zip_blob: bytes, *, artifact_file: str) -> tuple[bytes, str]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_blob)) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if not names:
                raise FetchEvidenceError("artifact_file_not_found")

            if artifact_file in names:
                return archive.read(artifact_file), artifact_file

            basename = Path(artifact_file).name
            fallback_candidates = [
                name for name in names if name == basename or name.endswith(f"/{basename}")
            ]
            if fallback_candidates:
                selected = sorted(fallback_candidates)[0]
                return archive.read(selected), selected
    except zipfile.BadZipFile as exc:
        raise FetchEvidenceError("invalid_artifact_archive") from exc

    raise FetchEvidenceError("artifact_file_not_found")


def fetch_latest_ai_quality_snapshot_evidence(
    *,
    repository: str,
    token: str,
    workflow_file: str,
    branch: str,
    artifact_name: str,
    artifact_file: str,
    timeout_seconds: float,
    fetch_json_fn: Callable[..., dict[str, Any]] = _http_get_json,
    fetch_bytes_fn: Callable[..., bytes] = _http_get_bytes,
) -> tuple[bytes, dict[str, Any]]:
    repo = _validate_repo(repository)
    auth_token = _validate_token(token)
    workflow_path = workflow_file.strip() or DEFAULT_WORKFLOW_FILE
    branch_name = branch.strip() or DEFAULT_BRANCH
    artifact_label = artifact_name.strip() or DEFAULT_ARTIFACT_NAME
    artifact_target = artifact_file.strip() or DEFAULT_ARTIFACT_FILE

    workflow_ref = parse.quote(workflow_path, safe="")
    query = parse.urlencode({"branch": branch_name, "status": "success", "per_page": 20})
    runs_url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_ref}/runs?{query}"
    runs_payload = fetch_json_fn(url=runs_url, token=auth_token, timeout_seconds=timeout_seconds)
    workflow_run_id = _resolve_workflow_run_id(runs_payload)

    artifacts_url = (
        f"https://api.github.com/repos/{repo}/actions/runs/{workflow_run_id}/artifacts?per_page=100"
    )
    artifacts_payload = fetch_json_fn(url=artifacts_url, token=auth_token, timeout_seconds=timeout_seconds)
    artifact_id, archive_download_url = _resolve_artifact(
        artifacts_payload,
        artifact_name=artifact_label,
    )

    archive_blob = fetch_bytes_fn(
        url=archive_download_url,
        token=auth_token,
        timeout_seconds=timeout_seconds,
    )
    file_bytes, archive_member = _extract_artifact_file(
        archive_blob,
        artifact_file=artifact_target,
    )

    meta = {
        "repository": repo,
        "workflow_file": workflow_path,
        "branch": branch_name,
        "workflow_run_id": workflow_run_id,
        "artifact_name": artifact_label,
        "artifact_id": artifact_id,
        "artifact_file": artifact_target,
        "archive_member": archive_member,
    }
    return file_bytes, meta


def _write_summary(path: str | None, payload: dict[str, Any]) -> None:
    if not path:
        return
    try:
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print("[ai-quality-evidence-fetch] warn: failed to write summary")
        print(f"  detail: {exc}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch latest daily AI quality snapshot evidence artifact from GitHub Actions."
    )
    parser.add_argument("--repo", default=None, help=f"GitHub repository (owner/name). Defaults to ${GITHUB_REPOSITORY_ENV_KEY}.")
    parser.add_argument("--token", default=None, help=f"GitHub token. Defaults to ${GITHUB_TOKEN_ENV_KEY}.")
    parser.add_argument("--workflow-file", default=DEFAULT_WORKFLOW_FILE)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--artifact-name", default=DEFAULT_ARTIFACT_NAME)
    parser.add_argument("--artifact-file", default=DEFAULT_ARTIFACT_FILE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--allow-missing-evidence", action="store_true")
    parser.add_argument("--summary-path", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    summary_path = (args.summary_path or "").strip() or None
    output_path = Path((args.output or "").strip() or DEFAULT_OUTPUT_PATH)
    repository = (args.repo or os.getenv(GITHUB_REPOSITORY_ENV_KEY, "")).strip()
    token = (args.token or os.getenv(GITHUB_TOKEN_ENV_KEY, "")).strip()
    allow_missing = bool(args.allow_missing_evidence)

    try:
        timeout_seconds = (
            float(args.timeout_seconds)
            if args.timeout_seconds is not None
            else _parse_positive_float(None, default=DEFAULT_TIMEOUT_SECONDS)
        )
    except ValueError as exc:
        print("[ai-quality-evidence-fetch] fail: invalid timeout")
        print(f"  detail: {exc}")
        _write_summary(
            summary_path,
            {"result": "fail", "reasons": ["invalid_timeout"], "meta": {}},
        )
        return 1

    print("[ai-quality-evidence-fetch] fetching daily artifact evidence")
    print(f"  repository: {repository or 'missing'}")
    print(f"  workflow_file: {args.workflow_file}")
    print(f"  branch: {args.branch}")
    print(f"  artifact_name: {args.artifact_name}")
    print(f"  artifact_file: {args.artifact_file}")
    print(f"  output: {output_path}")

    try:
        evidence_bytes, meta = fetch_latest_ai_quality_snapshot_evidence(
            repository=repository,
            token=token,
            workflow_file=args.workflow_file,
            branch=args.branch,
            artifact_name=args.artifact_name,
            artifact_file=args.artifact_file,
            timeout_seconds=timeout_seconds,
        )
    except FetchEvidenceError as exc:
        should_skip = allow_missing and exc.reason in SKIPPABLE_FAILURE_REASONS
        if should_skip:
            print("[ai-quality-evidence-fetch] skipped: missing evidence source")
            print(f"  reason: {exc.reason}")
            _write_summary(
                summary_path,
                {
                    "result": "skip",
                    "reasons": [exc.reason],
                    "meta": {
                        "repository": repository,
                        "workflow_file": args.workflow_file,
                        "branch": args.branch,
                        "artifact_name": args.artifact_name,
                        "artifact_file": args.artifact_file,
                        "output": str(output_path),
                    },
                },
            )
            return 0

        print("[ai-quality-evidence-fetch] fail: unable to fetch evidence")
        print(f"  reason: {exc.reason}")
        if exc.detail:
            print(f"  detail: {exc.detail}")
        _write_summary(
            summary_path,
            {
                "result": "fail",
                "reasons": [exc.reason],
                "meta": {
                    "repository": repository,
                    "workflow_file": args.workflow_file,
                    "branch": args.branch,
                    "artifact_name": args.artifact_name,
                    "artifact_file": args.artifact_file,
                    "output": str(output_path),
                },
            },
        )
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(evidence_bytes)
    summary_meta = dict(meta)
    summary_meta["output"] = str(output_path)

    print("[ai-quality-evidence-fetch] result: pass")
    print(f"  workflow_run_id: {summary_meta.get('workflow_run_id')}")
    print(f"  artifact_id: {summary_meta.get('artifact_id')}")
    print(f"  archive_member: {summary_meta.get('archive_member')}")
    _write_summary(
        summary_path,
        {"result": "pass", "reasons": [], "meta": summary_meta},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
