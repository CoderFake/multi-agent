"""All Redmine tool input schemas — unified imports."""

# --- Issue schemas ---
from agents.mcp_agents.redmine.schema.create_issue import CreateIssueInput
from agents.mcp_agents.redmine.schema.issues import (
    ListIssuesInput,
    GetIssueInput,
    UpdateIssueInput,
    DeleteIssueInput,
)
from agents.mcp_agents.redmine.schema.relations import (
    ListRelationsInput,
    CreateRelationInput,
    DeleteRelationInput,
)
from agents.mcp_agents.redmine.schema.watchers import (
    AddWatcherInput,
    RemoveWatcherInput,
)
from agents.mcp_agents.redmine.schema.categories import (
    ListCategoriesInput,
    CreateCategoryInput,
)

# --- Project schemas ---
from agents.mcp_agents.redmine.schema.projects import (
    ListProjectsInput,
    GetProjectInput,
    CreateProjectInput,
    UpdateProjectInput,
    DeleteProjectInput,
    ArchiveProjectInput,
)
from agents.mcp_agents.redmine.schema.members import ListMembersInput
from agents.mcp_agents.redmine.schema.versions import (
    ListVersionsInput,
    CreateVersionInput,
)

# --- Time entry schemas ---
from agents.mcp_agents.redmine.schema.log_time import LogTimeInput
from agents.mcp_agents.redmine.schema.time_entries import (
    ListTimeEntriesInput,
    UpdateTimeEntryInput,
    DeleteTimeEntryInput,
)

# --- Wiki schemas ---
from agents.mcp_agents.redmine.schema.wiki import (
    ListWikiPagesInput,
    GetWikiPageInput,
    UpdateWikiPageInput,
    DeleteWikiPageInput,
)

# --- Other schemas ---
from agents.mcp_agents.redmine.schema.search import SearchInput
from agents.mcp_agents.redmine.schema.form import (
    FetchFormContextInput,
    RequestUserInputInput,
)

__all__ = [
    # Issues
    "CreateIssueInput", "ListIssuesInput", "GetIssueInput",
    "UpdateIssueInput", "DeleteIssueInput",
    "ListRelationsInput", "CreateRelationInput", "DeleteRelationInput",
    "AddWatcherInput", "RemoveWatcherInput",
    "ListCategoriesInput", "CreateCategoryInput",
    # Projects
    "ListProjectsInput", "GetProjectInput", "CreateProjectInput",
    "UpdateProjectInput", "DeleteProjectInput", "ArchiveProjectInput",
    "ListMembersInput",
    "ListVersionsInput", "CreateVersionInput",
    # Time entries
    "LogTimeInput", "ListTimeEntriesInput",
    "UpdateTimeEntryInput", "DeleteTimeEntryInput",
    # Wiki
    "ListWikiPagesInput", "GetWikiPageInput",
    "UpdateWikiPageInput", "DeleteWikiPageInput",
    # Other
    "SearchInput", "FetchFormContextInput", "RequestUserInputInput",
]
