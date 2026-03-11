"""Redmine REST API tools for the ADK agent.

Credentials are injected per-request via session state:
  tool_context.state["redmine:url"]     — Redmine base URL
  tool_context.state["redmine:api_key"] — Redmine API key

All tools read these values from the ToolContext; they do NOT use environment
variables or global state.

Schema models live in schema/ — this file only contains tool functions.
"""

import asyncio
import logging
from typing import Optional

from google.adk.tools import FunctionTool, ToolContext

from agents.mcp_agents.redmine.client import RedmineClient
from agents.mcp_agents.redmine.schema import (
    # Issues
    CreateIssueInput, ListIssuesInput, GetIssueInput,
    UpdateIssueInput, DeleteIssueInput,
    ListRelationsInput, CreateRelationInput, DeleteRelationInput,
    AddWatcherInput, RemoveWatcherInput,
    ListCategoriesInput, CreateCategoryInput,
    # Projects
    ListProjectsInput, GetProjectInput, CreateProjectInput,
    UpdateProjectInput, DeleteProjectInput, ArchiveProjectInput,
    ListMembersInput,
    ListVersionsInput, CreateVersionInput,
    # Time entries
    LogTimeInput, ListTimeEntriesInput,
    UpdateTimeEntryInput, DeleteTimeEntryInput,
    # Wiki
    ListWikiPagesInput, GetWikiPageInput,
    UpdateWikiPageInput, DeleteWikiPageInput,
    # Other
    SearchInput, RequestUserInputInput,
)

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_client(tool_context: ToolContext) -> RedmineClient:
    """Get an authenticated RedmineClient from session state."""
    base_url = tool_context.state.get("redmine:url", "")
    api_key  = tool_context.state.get("redmine:api_key", "")
    if not base_url or not api_key:
        raise ValueError(
            "Redmine credentials not found in session. "
            "Please connect Redmine in Settings → Connections first."
        )
    return RedmineClient(base_url=base_url, api_key=api_key)


async def _build_options(tool_name: str, context: dict, client: RedmineClient) -> dict:
    """Fetch dynamic dropdown options from Redmine for form rendering.
    
    Uses Pydantic model json_schema_extra["fetch_action"] and ["depends_on"]
    to dynamically resolve and fetch options for each field.
    """
    options: dict = {}
    
    project_id = context.get("project_id")
    issue_id = context.get("issue_id")

    def _safe(result) -> dict:
        if isinstance(result, Exception):
            return {}
        if isinstance(result, dict) and result.get("error"):
            return {}
        return result

    # Pre-resolve project_id from issue_id if possible
    if not project_id and issue_id:
        issue = _safe(await client.get(f"/issues/{issue_id}.json"))
        proj = issue.get("issue", {}).get("project", {})
        if proj and "id" in proj:
            context["project_id"] = str(proj["id"])

    # ── Reusable fetchers ────────────────────────────────────────────────────
    
    async def fetch_projects() -> dict:
        res = _safe(await client.get("/projects.json", params={"limit": 100}))
        projects = res.get("projects", [])
        if not projects: return {}
        return {"enum": [str(p["id"]) for p in projects], "enumNames": [f'{p["name"]} ({p["identifier"]})' for p in projects]}

    async def fetch_trackers() -> dict:
        res = _safe(await client.get("/trackers.json"))
        trackers = res.get("trackers", [])
        if not trackers: return {}
        return {"enum": [t["id"] for t in trackers], "enumNames": [t["name"] for t in trackers]}

    async def fetch_statuses() -> dict:
        res = _safe(await client.get("/issue_statuses.json"))
        statuses = res.get("issue_statuses", [])
        if not statuses: return {}
        return {"enum": [s["id"] for s in statuses], "enumNames": [s["name"] for s in statuses]}

    async def fetch_priorities() -> dict:
        res = _safe(await client.get("/enumerations/issue_priorities.json"))
        priorities = res.get("issue_priorities", [])
        if not priorities: return {}
        return {"enum": [p["id"] for p in priorities], "enumNames": [p["name"] for p in priorities]}

    async def fetch_members(pid: str) -> dict:
        res = _safe(await client.get(f"/projects/{pid}/memberships.json", params={"limit": 100}))
        members = [m for m in res.get("memberships", []) if "user" in m]
        if not members: return {}
        return {"enum": [m["user"]["id"] for m in members], "enumNames": [m["user"]["name"] for m in members]}

    async def fetch_categories(pid: str) -> dict:
        res = _safe(await client.get(f"/projects/{pid}/issue_categories.json"))
        cats = res.get("issue_categories", [])
        if not cats: return {}
        return {"enum": [c["id"] for c in cats], "enumNames": [c["name"] for c in cats]}

    async def fetch_versions(pid: str) -> dict:
        res = _safe(await client.get(f"/projects/{pid}/versions.json"))
        versions = [v for v in res.get("versions", []) if v.get("status") == "open"]
        if not versions: return {}
        return {"enum": [v["id"] for v in versions], "enumNames": [v["name"] for v in versions]}

    async def fetch_activities() -> dict:
        res = _safe(await client.get("/enumerations/time_entry_activities.json"))
        activities = res.get("time_entry_activities", [])
        if not activities: return {}
        return {"enum": [a["id"] for a in activities], "enumNames": [a["name"] for a in activities]}

    async def fetch_issues(pid: Optional[str] = None) -> dict:
        params: dict = {"limit": 100, "status_id": "open"}
        if pid: params["project_id"] = pid
        res = _safe(await client.get("/issues.json", params=params))
        issues = res.get("issues", [])
        if not issues: return {}
        return {"enum": [i["id"] for i in issues], "enumNames": [f'#{i["id"]} {i["subject"]}' for i in issues]}

    fetchers_map = {
        "fetch_projects": fetch_projects,
        "fetch_trackers": fetch_trackers,
        "fetch_statuses": fetch_statuses,
        "fetch_priorities": fetch_priorities,
        "fetch_members": fetch_members,
        "fetch_categories": fetch_categories,
        "fetch_versions": fetch_versions,
        "fetch_activities": fetch_activities,
        "fetch_issues": fetch_issues,
    }

    # ── Map fields from Schema ───────────────────────────────────────────────
    from agents.mcp_agents.redmine.schema._registry import SCHEMA_REGISTRY
    model_class = SCHEMA_REGISTRY.get(tool_name)
    if not model_class:
        return options

    coros_to_run = []
    field_mapping = []

    for field_name, field_info in model_class.model_fields.items():
        extra = field_info.json_schema_extra or {}
        fetch_action = extra.get("fetch_action")

        if fetch_action and fetch_action in fetchers_map:
            depends_on = extra.get("depends_on", [])
            if isinstance(depends_on, str):
                depends_on = [depends_on]
                
            args_vals = []
            args_missing = False
            for dep in depends_on:
                val = context.get(dep)
                if val:
                    args_vals.append(val)
                else:
                    args_missing = True
                    break
            
            if not args_missing:
                coros_to_run.append(fetchers_map[fetch_action](*args_vals))
                field_mapping.append(field_name)

    if coros_to_run:
        results = await asyncio.gather(*coros_to_run, return_exceptions=True)
        for field_name, r in zip(field_mapping, results):
            if isinstance(r, dict) and r and not isinstance(r, Exception):
                # Ensure enum values match the expected field type if it's strictly integer
                # e.g Parent_id (from fetch_projects) needs ints
                field_type = model_class.model_fields[field_name].annotation
                try:
                    is_int_field = "int" in str(field_type).lower()
                    if is_int_field and r.get("enum"):
                        r["enum"] = [int(x) for x in r["enum"]]
                except Exception:
                    pass
                options[field_name] = r

    return options


# Keys the LLM commonly puts as context values (not dropdown data)
_PREFILL_KEYS = {"project_id", "project_name", "subject", "description", "issue_id", "spent_on"}


# ═══════════════════════════════════════════════════════════════════════════════
#  ISSUES
# ═══════════════════════════════════════════════════════════════════════════════

async def redmine_list_issues(input: ListIssuesInput, tool_context: ToolContext) -> dict:
    """List Redmine issues with optional filters. Use this to search and browse issues."""
    client = _get_client(tool_context)
    params = {"limit": input.limit, "offset": input.offset}
    if input.project_id:      params["project_id"]      = input.project_id
    if input.status_id:       params["status_id"]       = input.status_id
    if input.assigned_to_id:  params["assigned_to_id"]  = input.assigned_to_id
    if input.tracker_id:      params["tracker_id"]      = str(input.tracker_id)
    result = await client.get("/issues.json", params=params)
    issues = result.get("issues", [])
    return {
        "total_count": result.get("total_count", len(issues)),
        "issues": [
            {
                "id": i["id"],
                "subject": i["subject"],
                "status": i.get("status", {}).get("name"),
                "priority": i.get("priority", {}).get("name"),
                "assigned_to": i.get("assigned_to", {}).get("name") if i.get("assigned_to") else None,
                "project": i.get("project", {}).get("name"),
                "tracker": i.get("tracker", {}).get("name"),
                "category": i.get("category", {}).get("name") if i.get("category") else None,
                "fixed_version": i.get("fixed_version", {}).get("name") if i.get("fixed_version") else None,
                "due_date": i.get("due_date"),
                "done_ratio": i.get("done_ratio"),
                "updated_on": i.get("updated_on"),
            }
            for i in issues
        ],
    }


async def redmine_get_issue(input: GetIssueInput, tool_context: ToolContext) -> dict:
    """Get detailed information about a specific Redmine issue including comments and history."""
    client = _get_client(tool_context)
    params = {}
    if input.include:
        params["include"] = input.include
    result = await client.get(f"/issues/{input.issue_id}.json", params=params)
    return result.get("issue", result)


async def create_issue(input: CreateIssueInput, tool_context: ToolContext) -> dict:
    """Create a new Redmine issue. Call request_user_input first to collect form data."""
    client = _get_client(tool_context)
    data = input.model_dump(exclude_none=True)

    # Ensure integer types for ID fields (form dropdowns may pass strings)
    for int_field in ("tracker_id", "status_id", "priority_id", "assigned_to_id", "category_id", "fixed_version_id", "parent_issue_id", "done_ratio"):
        if int_field in data and data[int_field] is not None:
            try:
                data[int_field] = int(data[int_field])
            except (ValueError, TypeError):
                pass

    body = {"issue": data}
    logger.info("Creating issue with body: %s", body)

    result = await client.post("/issues.json", body=body)
    # Handle API errors gracefully
    if result.get("error"):
        return {"success": False, "message": result.get("message", "Unknown error"), "errors": result.get("errors", [])}
    issue = result.get("issue", {})
    return {
        "success": True,
        "issue_id": issue.get("id"),
        "subject": issue.get("subject"),
        "url": f"{tool_context.state.get('redmine:url', '')}/issues/{issue.get('id')}",
    }


async def redmine_update_issue(input: UpdateIssueInput, tool_context: ToolContext) -> dict:
    """Update fields of an existing Redmine issue."""
    client = _get_client(tool_context)
    data = input.model_dump(exclude_none=True)
    issue_id = data.pop("issue_id")

    for int_field in ("status_id", "priority_id", "assigned_to_id", "tracker_id", "category_id", "fixed_version_id", "done_ratio"):
        if int_field in data and data[int_field] is not None:
            try:
                data[int_field] = int(data[int_field])
            except (ValueError, TypeError):
                pass

    body = {"issue": data}
    logger.info("Updating issue %s with body: %s", issue_id, body)

    result = await client.put(f"/issues/{issue_id}.json", body=body)
    if result.get("error"):
        return {"success": False, "issue_id": issue_id, "message": result.get("message", "Unknown error"), "errors": result.get("errors", [])}

    updated_fields = list(data.keys())
    return {
        "success": True,
        "issue_id": issue_id,
        "updated_fields": updated_fields,
        "url": f"{tool_context.state.get('redmine:url', '')}/issues/{issue_id}",
        "message": f"Issue #{issue_id} updated: {', '.join(updated_fields)}",
    }


async def redmine_delete_issue(input: DeleteIssueInput, tool_context: ToolContext) -> dict:
    """Permanently delete a Redmine issue. This cannot be undone."""
    client = _get_client(tool_context)
    return await client.delete(f"/issues/{input.issue_id}.json")


# ── Issue Watchers ─────────────────────────────────────────────────────────────

async def redmine_add_watcher(input: AddWatcherInput, tool_context: ToolContext) -> dict:
    """Add a watcher to a Redmine issue."""
    client = _get_client(tool_context)
    return await client.post(f"/issues/{input.issue_id}/watchers.json", body={"user_id": input.user_id})


async def redmine_remove_watcher(input: RemoveWatcherInput, tool_context: ToolContext) -> dict:
    """Remove a watcher from a Redmine issue."""
    client = _get_client(tool_context)
    return await client.delete(f"/issues/{input.issue_id}/watchers/{input.user_id}.json")


# ── Issue Relations ────────────────────────────────────────────────────────────

async def redmine_list_relations(input: ListRelationsInput, tool_context: ToolContext) -> dict:
    """List all relations of a Redmine issue."""
    client = _get_client(tool_context)
    result = await client.get(f"/issues/{input.issue_id}/relations.json")
    return {"relations": result.get("relations", [])}


async def redmine_create_relation(input: CreateRelationInput, tool_context: ToolContext) -> dict:
    """Create a relation between two Redmine issues."""
    client = _get_client(tool_context)
    body = {"relation": {
        "issue_to_id": input.issue_to_id,
        "relation_type": input.relation_type or "relates",
    }}
    if input.delay is not None:
        body["relation"]["delay"] = input.delay
    result = await client.post(f"/issues/{input.issue_id}/relations.json", body=body)
    return result.get("relation", result)


async def redmine_delete_relation(input: DeleteRelationInput, tool_context: ToolContext) -> dict:
    """Delete an issue relation."""
    client = _get_client(tool_context)
    return await client.delete(f"/relations/{input.relation_id}.json")


# ── Issue Categories ───────────────────────────────────────────────────────────

async def redmine_list_categories(input: ListCategoriesInput, tool_context: ToolContext) -> dict:
    """List issue categories of a Redmine project."""
    client = _get_client(tool_context)
    result = await client.get(f"/projects/{input.project_id}/issue_categories.json")
    return {"categories": result.get("issue_categories", [])}


async def redmine_create_category(input: CreateCategoryInput, tool_context: ToolContext) -> dict:
    """Create a new issue category in a Redmine project."""
    client = _get_client(tool_context)
    body = {"issue_category": {"name": input.name}}
    if input.assigned_to_id:
        body["issue_category"]["assigned_to_id"] = input.assigned_to_id
    result = await client.post(f"/projects/{input.project_id}/issue_categories.json", body=body)
    return result.get("issue_category", result)


# ═══════════════════════════════════════════════════════════════════════════════
#  PROJECTS
# ═══════════════════════════════════════════════════════════════════════════════

async def redmine_list_projects(input: ListProjectsInput, tool_context: ToolContext) -> dict:
    """List all accessible Redmine projects."""
    client = _get_client(tool_context)
    params: dict = {"limit": input.limit}
    if input.include:
        params["include"] = input.include
    result = await client.get("/projects.json", params=params)
    projects = result.get("projects", [])
    return {
        "total": len(projects),
        "projects": [
            {"id": p["id"], "name": p["name"], "identifier": p.get("identifier"), "description": p.get("description", "")[:200]}
            for p in projects
        ],
    }


async def redmine_get_project(input: GetProjectInput, tool_context: ToolContext) -> dict:
    """Get details about a specific Redmine project."""
    client = _get_client(tool_context)
    result = await client.get(f"/projects/{input.project_id}.json")
    return result.get("project", result)


async def redmine_create_project(input: CreateProjectInput, tool_context: ToolContext) -> dict:
    """Create a new Redmine project."""
    client = _get_client(tool_context)
    data = input.model_dump(exclude_none=True)

    if "parent_id" in data and data["parent_id"] is not None:
        try:
            data["parent_id"] = int(data["parent_id"])
        except (ValueError, TypeError):
            pass

    body = {"project": data}
    logger.info("Creating project with body: %s", body)

    result = await client.post("/projects.json", body=body)
    if result.get("error"):
        return {"success": False, "message": result.get("message", "Unknown error"), "errors": result.get("errors", [])}
    
    project = result.get("project", {})
    return {
        "success": True,
        "project_id": project.get("id"),
        "name": project.get("name"),
        "identifier": project.get("identifier"),
    }


async def redmine_update_project(input: UpdateProjectInput, tool_context: ToolContext) -> dict:
    """Update a Redmine project."""
    client = _get_client(tool_context)
    data = input.model_dump(exclude_none=True)
    pid = data.pop("project_id")

    if "parent_id" in data and data["parent_id"] is not None:
        try:
            data["parent_id"] = int(data["parent_id"])
        except (ValueError, TypeError):
            pass

    body = {"project": data}
    logger.info("Updating project %s with body: %s", pid, body)

    result = await client.put(f"/projects/{pid}.json", body=body)
    if result.get("error"):
        return {"success": False, "project_id": pid, "message": result.get("message", "Unknown error"), "errors": result.get("errors", [])}
    
    return {"success": True, "project_id": pid, "message": f"Project {pid} updated successfully"}


async def redmine_delete_project(input: DeleteProjectInput, tool_context: ToolContext) -> dict:
    """Delete a Redmine project. This cannot be undone."""
    client = _get_client(tool_context)
    return await client.delete(f"/projects/{input.project_id}.json")


async def redmine_archive_project(input: ArchiveProjectInput, tool_context: ToolContext) -> dict:
    """Archive or unarchive a Redmine project."""
    client = _get_client(tool_context)
    action = "archive" if input.archive else "unarchive"
    return await client.put(f"/projects/{input.project_id}/{action}.json", body={})


# ── Members ────────────────────────────────────────────────────────────────────

async def redmine_list_members(input: ListMembersInput, tool_context: ToolContext) -> dict:
    """List members of a Redmine project."""
    client = _get_client(tool_context)
    result = await client.get(f"/projects/{input.project_id}/memberships.json", params={"limit": input.limit})
    members = [m for m in result.get("memberships", []) if "user" in m]
    return {
        "members": [
            {"id": m["user"]["id"], "name": m["user"]["name"]}
            for m in members
        ],
    }


# ── Versions ───────────────────────────────────────────────────────────────────

async def redmine_list_versions(input: ListVersionsInput, tool_context: ToolContext) -> dict:
    """List versions of a Redmine project (milestones)."""
    client = _get_client(tool_context)
    result = await client.get(f"/projects/{input.project_id}/versions.json")
    versions = result.get("versions", [])
    return {
        "versions": [
            {
                "id": v["id"], "name": v["name"], "status": v.get("status"),
                "due_date": v.get("due_date"), "description": v.get("description", "")[:200],
            }
            for v in versions
        ],
    }


async def redmine_create_version(input: CreateVersionInput, tool_context: ToolContext) -> dict:
    """Create a new version (milestone) in a Redmine project."""
    client = _get_client(tool_context)
    data = input.model_dump(exclude_none=True)
    pid = data.pop("project_id")
    
    body = {"version": data}
    logger.info("Creating version for project %s with body: %s", pid, body)

    result = await client.post(f"/projects/{pid}/versions.json", body=body)
    if result.get("error"):
        return {"success": False, "message": result.get("message", "Unknown error"), "errors": result.get("errors", [])}
    
    version = result.get("version", {})
    return {"success": True, "version_id": version.get("id"), "name": version.get("name")}


# ═══════════════════════════════════════════════════════════════════════════════
#  TIME ENTRIES
# ═══════════════════════════════════════════════════════════════════════════════

async def redmine_list_time_entries(input: ListTimeEntriesInput, tool_context: ToolContext) -> dict:
    """List time entries logged in Redmine."""
    client = _get_client(tool_context)
    params: dict = {"limit": input.limit}
    if input.project_id: params["project_id"] = input.project_id
    if input.issue_id:   params["issue_id"]   = str(input.issue_id)
    if input.user_id:    params["user_id"]    = str(input.user_id)
    if input.from_date:  params["from"]       = input.from_date
    if input.to_date:    params["to"]         = input.to_date
    result = await client.get("/time_entries.json", params=params)
    entries = result.get("time_entries", [])
    return {
        "total": result.get("total_count", len(entries)),
        "entries": [
            {
                "id": e["id"],
                "issue_id": e.get("issue", {}).get("id") if e.get("issue") else None,
                "project": e.get("project", {}).get("name"),
                "user": e.get("user", {}).get("name"),
                "hours": e["hours"],
                "activity": e.get("activity", {}).get("name"),
                "comments": e.get("comments"),
                "spent_on": e.get("spent_on"),
            }
            for e in entries
        ],
    }


async def log_time(input: LogTimeInput, tool_context: ToolContext) -> dict:
    """Log hours spent on a Redmine issue. Call request_user_input first to collect form data."""
    client = _get_client(tool_context)
    body = {"time_entry": input.model_dump(exclude_none=True)}
    result = await client.post("/time_entries.json", body=body)
    # Handle API errors gracefully
    if result.get("error"):
        return {"success": False, "message": result.get("message", "Unknown error"), "errors": result.get("errors", [])}
    entry = result.get("time_entry", {})
    return {
        "success": True,
        "time_entry_id": entry.get("id"),
        "hours": entry.get("hours"),
        "spent_on": entry.get("spent_on"),
    }


async def redmine_update_time_entry(input: UpdateTimeEntryInput, tool_context: ToolContext) -> dict:
    """Update an existing time entry."""
    client = _get_client(tool_context)
    data = input.model_dump(exclude_none=True)
    entry_id = data.pop("time_entry_id")

    for int_field in ("issue_id", "activity_id"):
        if int_field in data and data[int_field] is not None:
            try:
                data[int_field] = int(data[int_field])
            except (ValueError, TypeError):
                pass
                
    body = {"time_entry": data}
    logger.info("Updating time entry %s with body: %s", entry_id, body)

    result = await client.put(f"/time_entries/{entry_id}.json", body=body)
    if result.get("error"):
        return {"success": False, "time_entry_id": entry_id, "message": result.get("message", "Unknown error"), "errors": result.get("errors", [])}
        
    return {"success": True, "time_entry_id": entry_id, "message": f"Time entry {entry_id} updated successfully"}


async def redmine_delete_time_entry(input: DeleteTimeEntryInput, tool_context: ToolContext) -> dict:
    """Delete a time entry."""
    client = _get_client(tool_context)
    return await client.delete(f"/time_entries/{input.time_entry_id}.json")


# ═══════════════════════════════════════════════════════════════════════════════
#  WIKI PAGES
# ═══════════════════════════════════════════════════════════════════════════════

async def redmine_list_wiki_pages(input: ListWikiPagesInput, tool_context: ToolContext) -> dict:
    """List all wiki pages of a Redmine project."""
    client = _get_client(tool_context)
    result = await client.get(f"/projects/{input.project_id}/wiki/index.json")
    pages = result.get("wiki_pages", [])
    return {
        "wiki_pages": [
            {"title": p["title"], "version": p.get("version"), "updated_on": p.get("updated_on")}
            for p in pages
        ],
    }


async def redmine_get_wiki_page(input: GetWikiPageInput, tool_context: ToolContext) -> dict:
    """Get content of a specific wiki page."""
    client = _get_client(tool_context)
    path = f"/projects/{input.project_id}/wiki/{input.title}"
    if input.version:
        path += f"/{input.version}"
    result = await client.get(f"{path}.json", params={"include": "attachments"})
    return result.get("wiki_page", result)


async def redmine_update_wiki_page(input: UpdateWikiPageInput, tool_context: ToolContext) -> dict:
    """Create or update a wiki page (creates if it doesn't exist)."""
    client = _get_client(tool_context)
    body: dict = {"wiki_page": {"text": input.text}}
    if input.comments:
        body["wiki_page"]["comments"] = input.comments
    if input.version:
        body["wiki_page"]["version"] = input.version
    return await client.put(f"/projects/{input.project_id}/wiki/{input.title}.json", body=body)


async def redmine_delete_wiki_page(input: DeleteWikiPageInput, tool_context: ToolContext) -> dict:
    """Delete a wiki page and its history."""
    client = _get_client(tool_context)
    return await client.delete(f"/projects/{input.project_id}/wiki/{input.title}.json")


# ═══════════════════════════════════════════════════════════════════════════════
#  ENUMERATIONS & LOOKUP
# ═══════════════════════════════════════════════════════════════════════════════

async def redmine_list_priorities(tool_context: ToolContext) -> dict:
    """List all Redmine issue priority levels (e.g. Low, Normal, High, Urgent)."""
    client = _get_client(tool_context)
    result = await client.get("/enumerations/issue_priorities.json")
    return {"priorities": result.get("issue_priorities", [])}


async def redmine_list_trackers(tool_context: ToolContext) -> dict:
    """List all Redmine trackers (e.g. Bug, Feature, Support, Task)."""
    client = _get_client(tool_context)
    result = await client.get("/trackers.json")
    return {"trackers": result.get("trackers", [])}


async def redmine_list_statuses(tool_context: ToolContext) -> dict:
    """List all Redmine issue statuses (e.g. New, In Progress, Resolved, Closed)."""
    client = _get_client(tool_context)
    result = await client.get("/issue_statuses.json")
    return {"statuses": result.get("issue_statuses", [])}


async def redmine_list_activities(tool_context: ToolContext) -> dict:
    """List all Redmine time entry activity types (e.g. Development, Design, Testing)."""
    client = _get_client(tool_context)
    result = await client.get("/enumerations/time_entry_activities.json")
    return {"activities": result.get("time_entry_activities", [])}


async def redmine_list_roles(tool_context: ToolContext) -> dict:
    """List all Redmine roles."""
    client = _get_client(tool_context)
    result = await client.get("/roles.json")
    return {"roles": result.get("roles", [])}


async def redmine_list_queries(tool_context: ToolContext) -> dict:
    """List all saved custom queries."""
    client = _get_client(tool_context)
    result = await client.get("/queries.json")
    return {"queries": result.get("queries", [])}


async def redmine_my_account(tool_context: ToolContext) -> dict:
    """Get current user's account info."""
    client = _get_client(tool_context)
    result = await client.get("/my/account.json")
    return result.get("user", result)


# ═══════════════════════════════════════════════════════════════════════════════
#  SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

async def redmine_search(input: SearchInput, tool_context: ToolContext) -> dict:
    """Search across Redmine for issues, projects, or wiki pages."""
    client = _get_client(tool_context)
    params: dict = {
        "q": input.q,
        "limit": input.limit,
        "issues": 1 if input.issues else 0,
        "wiki_pages": 1 if input.wiki_pages else 0,
        "projects": 1 if input.projects else 0,
    }
    if input.scope:
        params["scope"] = input.scope
    result = await client.get("/search.json", params=params)
    return {
        "total": result.get("total_count", 0),
        "results": result.get("results", []),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  FORM RENDERING (intercepted by CopilotKit)
# ═══════════════════════════════════════════════════════════════════════════════

async def request_user_input(input: RequestUserInputInput, tool_context: ToolContext) -> dict:
    """Call this tool ONLY when you are missing required information to execute a creation/update tool, OR when the user explicitly asks to fill out a form.
    
    When you receive the return value from this tool (e.g., {"accepted": true, "data": {...}}), it means the user has filled out the form. You MUST EXPLICITLY ask the user for confirmation (e.g., "Are you sure you want to execute this action with the provided details?") BEFORE calling the target tool (e.g., `create_issue`). Wait for their confirmation before executing.
    
    If you ALREADY have the required information from the conversation, DO NOT call this tool. Call the target tool (e.g. `create_issue`) directly instead.

    ALWAYS fetches fresh dropdown data from Redmine. The LLM should just pass
    tool_name + project_id + form_defaults (pre-fill values).

    Flow:
      1. Resolve project_id from input.project_id / options / form_defaults
      2. Extract pre-fill values the LLM put in options → form_defaults
      3. Fetch real enum data from Redmine API (trackers, statuses, priorities,
         members, categories, versions for create_issue)
      4. Return {options: enum_data, form_defaults: prefill_values} for frontend
    """
    # Step 1: Resolve project_id from any source
    project_id = (
        input.project_id
        or input.options.get("project_id")
        or input.form_defaults.get("project_id")
    )

    # Step 2: Extract pre-fill values from options (LLM puts context here)
    form_defaults = dict(input.form_defaults)
    for key, value in input.options.items():
        if isinstance(value, dict) and "enum" in value:
            pass  # real enum data — ignore (we re-fetch)
        elif key in _PREFILL_KEYS and value:
            form_defaults.setdefault(key, value)
        elif key not in _PREFILL_KEYS and value and not isinstance(value, dict):
            form_defaults.setdefault(key, value)

    if not project_id and form_defaults.get("project_id"):
        project_id = str(form_defaults["project_id"])

    # Step 3: ALWAYS fetch real dropdown data
    enum_options: dict = {}
    try:
        client = _get_client(tool_context)
        enum_options = await _build_options(input.tool_name, project_id, client)
        logger.info(
            "request_user_input: fetched enum data for tool='%s', project='%s', fields=%s",
            input.tool_name, project_id, list(enum_options.keys())
        )
    except Exception as e:
        logger.warning("request_user_input: failed to fetch enum options: %s", e)

    # Step 4: Return — intercepted by frontend CopilotKit action
    return {
        "status":        "awaiting_user_input",
        "tool_name":     input.tool_name,
        "options":       enum_options,
        "form_defaults": form_defaults,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  TOOL EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

ALL_TOOLS = [
    # Issues
    FunctionTool(func=redmine_list_issues),
    FunctionTool(func=redmine_get_issue),
    FunctionTool(func=create_issue),
    FunctionTool(func=redmine_update_issue),
    FunctionTool(func=redmine_delete_issue),
    FunctionTool(func=redmine_add_watcher),
    FunctionTool(func=redmine_remove_watcher),
    FunctionTool(func=redmine_list_relations),
    FunctionTool(func=redmine_create_relation),
    FunctionTool(func=redmine_delete_relation),
    FunctionTool(func=redmine_list_categories),
    FunctionTool(func=redmine_create_category),
    # Projects
    FunctionTool(func=redmine_list_projects),
    FunctionTool(func=redmine_get_project),
    FunctionTool(func=redmine_create_project),
    FunctionTool(func=redmine_update_project),
    FunctionTool(func=redmine_delete_project),
    FunctionTool(func=redmine_archive_project),
    FunctionTool(func=redmine_list_members),
    FunctionTool(func=redmine_list_versions),
    FunctionTool(func=redmine_create_version),
    # Time entries
    FunctionTool(func=redmine_list_time_entries),
    FunctionTool(func=log_time),
    FunctionTool(func=redmine_update_time_entry),
    FunctionTool(func=redmine_delete_time_entry),
    # Wiki
    FunctionTool(func=redmine_list_wiki_pages),
    FunctionTool(func=redmine_get_wiki_page),
    FunctionTool(func=redmine_update_wiki_page),
    FunctionTool(func=redmine_delete_wiki_page),
    # Enumerations & lookup
    FunctionTool(func=redmine_list_priorities),
    FunctionTool(func=redmine_list_trackers),
    FunctionTool(func=redmine_list_statuses),
    FunctionTool(func=redmine_list_activities),
    FunctionTool(func=redmine_list_roles),
    FunctionTool(func=redmine_list_queries),
    FunctionTool(func=redmine_my_account),
    # Search
    FunctionTool(func=redmine_search),
    # Form
    FunctionTool(func=request_user_input),
]
