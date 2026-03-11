"""Custom tools for the GitLab agent.

These Python tools call the GitLab REST API directly as replacements for the
deprecated/broken @modelcontextprotocol/server-gitlab MCP tools.

MCP audit results (gitlab.newwave.vn self-hosted):
  get_file_contents  — works fine via MCP (kept in mcp.json)
  search_repositories — broken: 'Cannot read properties of undefined (reading map)'
  write tools (create_*/ push_files / fork) — not tested, may work

All read-oriented tools replaced here with direct REST calls that are reliable.
Write tools also provided here as safety net in case MCP write tools break.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _client(token: str, base_url: str) -> httpx.Client:
    """Build a synchronous httpx client pre-configured for GitLab REST API."""
    return httpx.Client(
        base_url=base_url.rstrip("/"),
        headers={"PRIVATE-TOKEN": token, "Content-Type": "application/json"},
        timeout=30,
    )


def _get_gitlab_config(tool_context) -> tuple[str, str]:
    """Extract PAT and base URL from tool_context session state.

    Returns:
        (token, base_url) tuple, e.g. ('glpat-...', 'https://gitlab.newwave.vn/api/v4')
    """
    state = tool_context.state if tool_context else {}
    token = state.get("gitlab:token", "")
    base_url = state.get("gitlab:url", "https://gitlab.com/api/v4")
    return token, base_url


# ---------------------------------------------------------------------------
# Project tools (replaces broken search_repositories)
# ---------------------------------------------------------------------------

def gitlab_list_projects(
    search: str = "",
    owned: bool = False,
    membership: bool = True,
    per_page: int = 20,
    tool_context=None,
) -> dict:
    """List GitLab projects accessible to the authenticated user.

    Args:
        search: Optional keyword to filter projects by name.
        owned: If True, return only projects owned by the user.
        membership: If True, return only projects the user is a member of.
        per_page: Number of results to return (max 100).

    Returns:
        A dict with 'projects' list, each containing id, name, path, description, web_url.
    """
    token, base_url = _get_gitlab_config(tool_context)
    if not token:
        return {"error": "GitLab token not configured. Please connect GitLab in Settings."}

    params = {
        "per_page": min(per_page, 100),
        "simple": "true",
        "order_by": "last_activity_at",
    }
    if search:
        params["search"] = search
    if owned:
        params["owned"] = "true"
    if membership:
        params["membership"] = "true"

    try:
        with _client(token, base_url) as client:
            resp = client.get("/projects", params=params)
            resp.raise_for_status()
            data = resp.json()

        projects = [
            {
                "id": p["id"],
                "name": p["name"],
                "path": p.get("path_with_namespace", p["path"]),
                "description": p.get("description") or "",
                "web_url": p.get("web_url", ""),
                "default_branch": p.get("default_branch", "main"),
                "last_activity_at": p.get("last_activity_at", ""),
            }
            for p in data
        ]
        return {"projects": projects, "count": len(projects)}

    except httpx.HTTPStatusError as e:
        return {"error": f"GitLab API error {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": f"Request failed: {e}"}


# ---------------------------------------------------------------------------
# Issue tools
# ---------------------------------------------------------------------------

def gitlab_list_issues(
    project_id: str,
    state: str = "opened",
    per_page: int = 20,
    tool_context=None,
) -> dict:
    """List issues in a GitLab project.

    Args:
        project_id: Project path (e.g. 'mygroup/myproject') or numeric ID.
        state: Filter by state — 'opened', 'closed', or 'all'.
        per_page: Number of results (max 100).

    Returns:
        A dict with 'issues' list.
    """
    token, base_url = _get_gitlab_config(tool_context)
    if not token:
        return {"error": "GitLab token not configured."}

    import urllib.parse
    encoded = urllib.parse.quote(str(project_id), safe="")

    try:
        with _client(token, base_url) as client:
            resp = client.get(
                f"/projects/{encoded}/issues",
                params={"state": state, "per_page": min(per_page, 100), "order_by": "updated_at"},
            )
            resp.raise_for_status()
            data = resp.json()

        issues = [
            {
                "id": i["iid"],
                "title": i["title"],
                "state": i["state"],
                "author": i["author"]["name"],
                "assignees": [a["name"] for a in i.get("assignees", [])],
                "labels": i.get("labels", []),
                "created_at": i.get("created_at", ""),
                "updated_at": i.get("updated_at", ""),
                "web_url": i.get("web_url", ""),
            }
            for i in data
        ]
        return {"issues": issues, "count": len(issues)}

    except httpx.HTTPStatusError as e:
        return {"error": f"GitLab API error {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": f"Request failed: {e}"}


def gitlab_create_issue(
    project_id: str,
    title: str,
    description: str = "",
    labels: str = "",
    tool_context=None,
) -> dict:
    """Create a new issue in a GitLab project.

    Args:
        project_id: Project path or numeric ID.
        title: Issue title.
        description: Issue body (Markdown supported).
        labels: Comma-separated list of label names.

    Returns:
        Created issue info with id and web_url.
    """
    token, base_url = _get_gitlab_config(tool_context)
    if not token:
        return {"error": "GitLab token not configured."}

    import urllib.parse
    encoded = urllib.parse.quote(str(project_id), safe="")

    body = {"title": title, "description": description}
    if labels:
        body["labels"] = labels

    try:
        with _client(token, base_url) as client:
            resp = client.post(f"/projects/{encoded}/issues", json=body)
            resp.raise_for_status()
            i = resp.json()

        return {
            "id": i["iid"],
            "title": i["title"],
            "web_url": i.get("web_url", ""),
            "state": i["state"],
        }

    except httpx.HTTPStatusError as e:
        return {"error": f"GitLab API error {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": f"Request failed: {e}"}


# ---------------------------------------------------------------------------
# Merge Request tools
# ---------------------------------------------------------------------------

def gitlab_list_merge_requests(
    project_id: str,
    state: str = "opened",
    per_page: int = 20,
    tool_context=None,
) -> dict:
    """List merge requests in a GitLab project.

    Args:
        project_id: Project path or numeric ID.
        state: Filter by state — 'opened', 'closed', 'merged', or 'all'.
        per_page: Number of results (max 100).

    Returns:
        A dict with 'merge_requests' list.
    """
    token, base_url = _get_gitlab_config(tool_context)
    if not token:
        return {"error": "GitLab token not configured."}

    import urllib.parse
    encoded = urllib.parse.quote(str(project_id), safe="")

    try:
        with _client(token, base_url) as client:
            resp = client.get(
                f"/projects/{encoded}/merge_requests",
                params={"state": state, "per_page": min(per_page, 100), "order_by": "updated_at"},
            )
            resp.raise_for_status()
            data = resp.json()

        mrs = [
            {
                "id": mr["iid"],
                "title": mr["title"],
                "state": mr["state"],
                "author": mr["author"]["name"],
                "source_branch": mr["source_branch"],
                "target_branch": mr["target_branch"],
                "web_url": mr.get("web_url", ""),
                "updated_at": mr.get("updated_at", ""),
            }
            for mr in data
        ]
        return {"merge_requests": mrs, "count": len(mrs)}

    except httpx.HTTPStatusError as e:
        return {"error": f"GitLab API error {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": f"Request failed: {e}"}


# ---------------------------------------------------------------------------
# Pipeline / CI tools
# ---------------------------------------------------------------------------

def gitlab_list_pipelines(
    project_id: str,
    per_page: int = 10,
    tool_context=None,
) -> dict:
    """List recent CI/CD pipelines for a GitLab project.

    Args:
        project_id: Project path or numeric ID.
        per_page: Number of pipelines to return (max 100).

    Returns:
        A dict with 'pipelines' list including status and web_url.
    """
    token, base_url = _get_gitlab_config(tool_context)
    if not token:
        return {"error": "GitLab token not configured."}

    import urllib.parse
    encoded = urllib.parse.quote(str(project_id), safe="")

    try:
        with _client(token, base_url) as client:
            resp = client.get(
                f"/projects/{encoded}/pipelines",
                params={"per_page": min(per_page, 100), "order_by": "updated_at"},
            )
            resp.raise_for_status()
            data = resp.json()

        pipelines = [
            {
                "id": p["id"],
                "status": p["status"],
                "ref": p["ref"],
                "sha": p["sha"][:8],
                "created_at": p.get("created_at", ""),
                "web_url": p.get("web_url", ""),
            }
            for p in data
        ]
        return {"pipelines": pipelines, "count": len(pipelines)}

    except httpx.HTTPStatusError as e:
        return {"error": f"GitLab API error {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": f"Request failed: {e}"}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

CUSTOM_TOOLS: list = [
    gitlab_list_projects,
    gitlab_list_issues,
    gitlab_create_issue,
    gitlab_list_merge_requests,
    gitlab_list_pipelines,
]
