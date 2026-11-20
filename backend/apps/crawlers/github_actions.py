import re

import httpx
from django.conf import settings


class WorkflowDispatchError(Exception):
    pass


def dispatch_crawl_workflow(run_ids):
    token = getattr(settings, "GITHUB_ACTIONS_TOKEN", "").strip()
    repository = getattr(settings, "GITHUB_REPOSITORY", "").strip()
    workflow_file = getattr(settings, "GITHUB_WORKFLOW_FILE", "data-jobs.yml").strip()
    ref = getattr(settings, "GITHUB_ACTIONS_REF", "main").strip()

    if not token:
        raise WorkflowDispatchError(
            "GitHub Actions dispatch is not configured on this service."
        )
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise WorkflowDispatchError("GITHUB_REPOSITORY is not configured correctly.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", workflow_file):
        raise WorkflowDispatchError("GITHUB_WORKFLOW_FILE is not configured correctly.")
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", ref) or ref.startswith("-"):
        raise WorkflowDispatchError("GITHUB_ACTIONS_REF is not configured correctly.")

    url = (
        f"https://api.github.com/repos/{repository}/actions/workflows/"
        f"{workflow_file}/dispatches"
    )
    try:
        response = httpx.post(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "ref": ref,
                "inputs": {
                    "operation": "news",
                    "crawl_run_ids": ",".join(str(run_id) for run_id in run_ids),
                    "source_keys": "",
                    "run_legacy_queue_worker": "false",
                },
            },
            timeout=10,
        )
    except httpx.RequestError as exc:
        raise WorkflowDispatchError(
            "Could not connect to GitHub Actions to dispatch the crawl workflow."
        ) from exc

    if response.status_code != 204:
        raise WorkflowDispatchError(
            f"GitHub Actions rejected the workflow dispatch (HTTP {response.status_code})."
        )
