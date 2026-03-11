"""BigQuery tools for the data analyst agent.

Access control is handled by the service account's IAM permissions.
Queries run with whatever BigQuery access the service account has.
"""

import logging
import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import uuid4

from google.adk.tools import ToolContext
from google.cloud import bigquery

from config.settings import settings

logger = logging.getLogger(__name__)


def _to_json_safe(value: Any) -> Any:
    """Convert BigQuery values to JSON-serializable types."""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_json_safe(v) for k, v in value.items()}
    return value


def _row_to_json_safe(row: Any) -> list:
    """Convert a BigQuery row to JSON-serializable list."""
    return [_to_json_safe(v) for v in row.values()]


# Display limit for tabular view (charts use full data)
TABLE_DISPLAY_LIMIT = 1000


def _get_client() -> bigquery.Client:
    """Get BigQuery client with project from settings."""
    if not settings.GOOGLE_CLOUD_PROJECT:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable required")
    return bigquery.Client(project=settings.GOOGLE_CLOUD_PROJECT)


def _suggest_chart_type(
    columns: list[dict], row_count: int, rows: list[list] | None = None
) -> str:
    """Suggest chart type based on result shape and data characteristics.

    Chart selection priority:
    1. Single value → metric card
    2. Time-series (DATE/TIMESTAMP first column) → line chart
    3. Small categorical (≤7 rows, 2 columns) → pie chart
    4. Text-heavy data in first column (long strings) → table
    5. Aggregated data with categories → bar chart
    """
    if row_count == 1 and len(columns) == 1:
        return "metric"

    if len(columns) < 2:
        return "table"

    first_col_type = columns[0].get("type", "").upper()

    # Time-series data → line chart (check first, before text detection)
    if first_col_type in ("DATE", "TIMESTAMP", "DATETIME"):
        return "line"

    # Small categorical data → pie chart
    if row_count <= 7 and len(columns) == 2:
        return "pie"

    # Check if first column contains long text (commits, descriptions, etc.)
    # Only applies when first column is STRING - indicates detailed records
    if first_col_type in ("STRING", "BYTES") and rows and len(rows) > 0:
        sample_values = [
            row[0] for row in rows[:20] if row[0] is not None
        ]
        if sample_values:
            avg_len = sum(len(str(v)) for v in sample_values) / len(sample_values)
            # Long strings (>30 chars avg) in first column → table for readability
            if avg_len > 30:
                return "table"

    return "bar"


def _extract_title_from_query(query: str) -> str:
    """Extract a human-readable title from SQL query."""
    match = re.search(r"SELECT\s+(.+?)\s+FROM", query, re.IGNORECASE | re.DOTALL)
    if match:
        columns = match.group(1).strip()
        columns = re.sub(r"\s+", " ", columns)[:50]
        if columns != "*":
            return f"Query: {columns}..."
    return "Query Result"


def _track_query_attempt(
    tool_context: ToolContext,
    query: str,
    success: bool,
    error: str | None = None,
    bytes_processed: int = 0,
    row_count: int = 0,
) -> None:
    """Track a query attempt in session state for frontend display.

    The capture_query_attempts callback reads this and embeds in the response.
    """
    attempts = tool_context.state.get("query_attempts", [])
    attempts.append(
        {
            "query": query,
            "success": success,
            "error": error,
            "bytes_processed": bytes_processed,
            "row_count": row_count,
        }
    )
    tool_context.state["query_attempts"] = attempts


async def create_chart(
    title: str,
    columns: list[str],
    rows: list[list],
    tool_context: ToolContext,
    chart_type: str = "",
) -> dict[str, Any]:
    """Create a chart widget from pre-structured data (not from BigQuery).

    Use this tool when you receive structured data from another source (e.g.
    search results summarised by the root agent) and need to visualise it.
    Do NOT use this for BigQuery queries — use query_data instead.

    Args:
        title: Human-readable title for the chart widget.
        columns: List of column names (e.g. ["Country", "Population"]).
        rows: List of rows, each row a list of values matching the columns.
        tool_context: ADK tool context with session state access.
        chart_type: Optional chart type hint. One of "bar", "line", "pie",
            "table", "metric". If empty, auto-detected from the data shape.

    Returns:
        Widget metadata including the assigned widget ID and chart type.
    """
    valid_types = {"bar", "line", "pie", "table", "metric"}

    if not columns or not rows:
        return {"success": False, "error": "columns and rows must be non-empty"}

    # Build column schema for chart type suggestion
    col_schema = [{"name": c, "type": "STRING"} for c in columns]

    if chart_type and chart_type in valid_types:
        resolved_chart = chart_type
    else:
        resolved_chart = _suggest_chart_type(col_schema, len(rows), rows)

    widget_id = str(uuid4())
    widget = {
        "id": widget_id,
        "title": title,
        "chart_type": resolved_chart,
        "data": {
            "columns": columns,
            "rows": rows,
        },
        "total_rows": len(rows),
    }

    pending_widgets = tool_context.state.get("pending_widgets", [])
    pending_widgets.append(widget)
    tool_context.state["pending_widgets"] = pending_widgets

    logger.info(f"Chart widget {widget_id} ({resolved_chart}) added to pending_widgets")

    return {
        "success": True,
        "widget_id": widget_id,
        "chart_type": resolved_chart,
        "row_count": len(rows),
    }


async def query_data(
    query: str,
    tool_context: ToolContext,
    title: str = "",
) -> dict[str, Any]:
    """Execute a BigQuery SQL query.

    Results are returned for display and automatically added to the dashboard
    as a widget. Access is controlled by the service account's IAM
    permissions - you can query any table the service account can access.

    Each query attempt (success or failure) is tracked in session state.
    Use get_query_attempts_tag() to retrieve the history for display.

    Args:
        query: SQL query string. Use fully-qualified table names
            (project.dataset.table) or backtick notation (`project.dataset.table`).
        tool_context: ADK tool context with session state access.
        title: Optional title for the dashboard widget. Auto-generated if not provided.

    Returns:
        Query results with columns, rows, and visualisation metadata.
        Also stored in session state for frontend dashboard rendering.
    """
    try:
        client = _get_client()
        logger.info(f"Executing BigQuery: {query[:200]}...")

        query_job = client.query(query)
        result = query_job.result()

        # Extract schema
        columns = [
            {"name": field.name, "type": field.field_type} for field in result.schema
        ]

        # Fetch all rows (for charts - frontend limits table display)
        rows = [_row_to_json_safe(row) for row in result]
        total_rows = len(rows)

        suggested_chart = _suggest_chart_type(columns, total_rows, rows)
        bytes_processed = query_job.total_bytes_processed or 0

        logger.info(
            f"Query complete: {total_rows} rows, "
            f"{bytes_processed / 1024**3:.2f} GB processed, "
            f"job_id={query_job.job_id}"
        )

        # Track successful attempt
        _track_query_attempt(
            tool_context,
            query=query,
            success=True,
            bytes_processed=bytes_processed,
            row_count=total_rows,
        )

        # Create widget for frontend dashboard
        widget_id = str(uuid4())
        widget = {
            "id": widget_id,
            "query_id": query_job.job_id,
            "title": title if title else _extract_title_from_query(query),
            "chart_type": suggested_chart,
            "data": {
                "columns": [c["name"] for c in columns],
                "rows": rows,
            },
            "query": query,
            "total_rows": total_rows,
            "table_display_limit": TABLE_DISPLAY_LIMIT,
            "bytes_processed": bytes_processed,
        }

        # Store in session state for frontend
        pending_widgets = tool_context.state.get("pending_widgets", [])
        pending_widgets.append(widget)
        tool_context.state["pending_widgets"] = pending_widgets

        logger.info(f"Query successful, widget {widget_id} added to pending_widgets")

        return {
            "success": True,
            "query": query,
            "columns": [c["name"] for c in columns],
            "row_count": total_rows,
            "suggested_chart": suggested_chart,
            "widget_id": widget_id,
            "bytes_processed": bytes_processed,
        }

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Query execution failed: {error_msg}")

        # Track failed attempt
        _track_query_attempt(
            tool_context,
            query=query,
            success=False,
            error=error_msg,
        )

        return {
            "error": f"Query failed: {error_msg}",
            "success": False,
        }


async def describe_table(
    table_id: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Get detailed schema for a specific BigQuery table.

    Returns column names, data types, and sample values to help write queries.
    Use this to understand the structure of a dataset before querying.

    Args:
        table_id: Full table ID (project.dataset.table).
        tool_context: ADK tool context with session state access.

    Returns:
        Table schema with column types and sample data, or error if not accessible.
    """
    try:
        parts = table_id.split(".")
        if len(parts) != 3:
            return {
                "error": f"Invalid table_id format. Expected 'project.dataset.table', got '{table_id}'",
                "success": False,
            }

        project, dataset, table = parts
        client = _get_client()

        # Get schema via INFORMATION_SCHEMA
        schema_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """

        schema_job = client.query(schema_query)
        schema_result = schema_job.result()

        columns = [
            {
                "name": row.column_name,
                "type": row.data_type,
                "nullable": row.is_nullable == "YES",
            }
            for row in schema_result
        ]

        # Get sample data
        sample_query = f"SELECT * FROM `{table_id}` LIMIT 5"
        sample_job = client.query(sample_query)
        sample_result = sample_job.result()

        sample_columns = [field.name for field in sample_result.schema]
        sample_rows = [_row_to_json_safe(row) for row in sample_result]

        # Get approximate row count
        count_query = f"""
            SELECT row_count
            FROM `{project}.{dataset}.__TABLES__`
            WHERE table_id = '{table}'
        """

        try:
            count_job = client.query(count_query)
            count_result = list(count_job.result())
            row_count = count_result[0].row_count if count_result else "Unknown"
        except Exception:
            row_count = "Unknown"

        return {
            "success": True,
            "table_id": table_id,
            "columns": columns,
            "row_count": row_count,
            "sample_data": {
                "columns": sample_columns,
                "rows": sample_rows,
            },
        }

    except Exception as e:
        logger.exception(f"Failed to describe table {table_id}: {e}")
        return {
            "error": f"Failed to describe table: {e!s}",
            "success": False,
        }


def list_datasets(tool_context: ToolContext) -> dict[str, Any]:
    """List BigQuery datasets accessible to the agent.

    Returns datasets and tables that the service account can access.
    Use this to discover what data sources are available before writing queries.

    Args:
        tool_context: ADK tool context with session state access.

    Returns:
        List of accessible datasets with their tables.
    """
    try:
        client = _get_client()
        project = settings.GOOGLE_CLOUD_PROJECT

        datasets = []
        for dataset in client.list_datasets():
            dataset_id = dataset.dataset_id
            tables = []

            try:
                for table in client.list_tables(dataset.reference):
                    tables.append(
                        {
                            "table_id": f"{project}.{dataset_id}.{table.table_id}",
                            "type": table.table_type,
                        }
                    )
            except Exception as e:
                logger.warning(f"Could not list tables in {dataset_id}: {e}")

            datasets.append(
                {
                    "dataset_id": dataset_id,
                    "full_id": f"{project}.{dataset_id}",
                    "tables": tables,
                }
            )

        return {
            "success": True,
            "project": project,
            "datasets": datasets,
        }

    except Exception as e:
        logger.exception(f"Failed to list datasets: {e}")
        return {
            "error": f"Failed to list datasets: {e!s}",
            "success": False,
        }
