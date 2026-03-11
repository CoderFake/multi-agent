"""Async HTTP client for Redmine REST API."""

import httpx
from typing import Optional


class RedmineClient:
    """Async HTTP client wrapping Redmine REST API.

    Authenticates via X-Redmine-API-Key header.
    All methods return parsed JSON as a Python dict.
    On 4xx/5xx errors, returns {"error": ..., "status": ...} instead of crashing.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "X-Redmine-API-Key": api_key,
            "Content-Type": "application/json",
        }

    def _handle_error(self, response: httpx.Response) -> dict:
        """Extract error details from a failed response."""
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}

        errors = body.get("errors", [])
        return {
            "error": True,
            "status": response.status_code,
            "errors": errors if errors else [response.text],
            "message": "; ".join(errors) if errors else f"HTTP {response.status_code}: {response.text[:200]}",
        }

    async def get(self, path: str, params: Optional[dict] = None) -> dict:
        """Perform an authenticated GET request."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self._base_url}{path}",
                headers=self._headers,
                params=params or {},
            )
            if not response.is_success:
                return self._handle_error(response)
            return response.json()

    async def post(self, path: str, body: dict) -> dict:
        """Perform an authenticated POST request."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self._base_url}{path}",
                headers=self._headers,
                json=body,
            )
            if not response.is_success:
                return self._handle_error(response)
            return response.json()

    async def put(self, path: str, body: dict) -> dict:
        """Perform an authenticated PUT request."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.put(
                f"{self._base_url}{path}",
                headers=self._headers,
                json=body,
            )
            if not response.is_success:
                return self._handle_error(response)
            # PUT returns 204 No Content — no JSON body
            if response.status_code == 204:
                return {"success": True}
            return response.json()

    async def delete(self, path: str) -> dict:
        """Perform an authenticated DELETE request."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                f"{self._base_url}{path}",
                headers=self._headers,
            )
            if not response.is_success:
                return self._handle_error(response)
            return {"success": True}
