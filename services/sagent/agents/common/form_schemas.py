from typing import Any, Optional, Dict
from pydantic import Field

def DynamicDropdownField(
    description: str,
    fetch_action: str,
    depends_on: Optional[str | list[str]] = None,
    default: Any = ...,
    **kwargs: Any
) -> Any:
    """Helper for dropdowns populated dynamically from the API."""
    extra = {
        "dynamic_dropdown": True,
        "fetch_action": fetch_action
    }
    if depends_on:
        extra["depends_on"] = depends_on
        
    if "json_schema_extra" in kwargs:
        extra.update(kwargs.pop("json_schema_extra"))
        
    return Field(default, description=description, json_schema_extra=extra, **kwargs)

def RichTextField(
    description: str,
    default: Any = ...,
    **kwargs: Any
) -> Any:
    """Helper for fields that should render as a rich text editor UI."""
    extra = {"ui:widget": "richtext"}
    if "json_schema_extra" in kwargs:
        extra.update(kwargs.pop("json_schema_extra"))
        
    return Field(default, description=description, json_schema_extra=extra, **kwargs)

def FileUploadField(
    description: str,
    accept: str = "*/*",
    multiple: bool = False,
    default: Any = ...,
    **kwargs: Any
) -> Any:
    """Helper for file upload fields.
    
    Args:
        description: Field description.
        accept: Comma-separated list of accepted file types (e.g. "image/*, .pdf").
        multiple: Whether to allow multiple files.
    """
    extra = {
        "ui:widget": "files" if multiple else "file",
        "ui:options": {
            "accept": accept
        }
    }
    if "json_schema_extra" in kwargs:
        extra.update(kwargs.pop("json_schema_extra"))
        
    return Field(default, description=description, json_schema_extra=extra, **kwargs)
