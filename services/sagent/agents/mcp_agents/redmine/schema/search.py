"""Search input schema."""

from typing import Optional
from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    """Input for searching across Redmine."""
    q:          str           = Field(..., description="Search query keywords")
    scope:      Optional[str] = Field(None, description="'all', 'my_project', or 'subprojects'")
    issues:     bool          = Field(True,  description="Include issues in search")
    wiki_pages: bool          = Field(False, description="Include wiki pages in search")
    projects:   bool          = Field(False, description="Include projects in search")
    limit:      int           = Field(25, description="Max results")
