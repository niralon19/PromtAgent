from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

log = structlog.get_logger(__name__)


class JiraError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Jira API error {status_code}: {message}")


class JiraClient:
    """Async Jira REST API client with retries."""

    def __init__(self) -> None:
        self._base = (settings.jira_url or "").rstrip("/")
        self._auth = (settings.jira_user or "", settings.jira_token or "")
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base,
            auth=self._auth,
            headers=self._headers,
            timeout=30.0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def create_issue(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Create a Jira issue. Returns the created issue dict."""
        async with self._client() as client:
            resp = await client.post("/rest/api/3/issue", json={"fields": fields})
            self._raise_for_status(resp)
            data = resp.json()
            log.info("jira_issue_created", key=data.get("key"), id=data.get("id"))
            return data

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def update_issue(self, issue_key: str, fields: dict[str, Any]) -> None:
        async with self._client() as client:
            resp = await client.put(f"/rest/api/3/issue/{issue_key}", json={"fields": fields})
            self._raise_for_status(resp)
            log.info("jira_issue_updated", key=issue_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def add_comment(self, issue_key: str, body: dict[str, Any]) -> None:
        """Add an ADF comment to a Jira issue."""
        async with self._client() as client:
            resp = await client.post(
                f"/rest/api/3/issue/{issue_key}/comment",
                json={"body": body},
            )
            self._raise_for_status(resp)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def transition_issue(self, issue_key: str, transition_name: str) -> None:
        """Transition an issue by status name."""
        async with self._client() as client:
            # Fetch available transitions
            resp = await client.get(f"/rest/api/3/issue/{issue_key}/transitions")
            self._raise_for_status(resp)
            transitions = resp.json().get("transitions", [])
            target = next(
                (t for t in transitions if t["name"].lower() == transition_name.lower()), None
            )
            if target is None:
                raise JiraError(404, f"Transition '{transition_name}' not found on {issue_key}")

            resp2 = await client.post(
                f"/rest/api/3/issue/{issue_key}/transitions",
                json={"transition": {"id": target["id"]}},
            )
            self._raise_for_status(resp2)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_issue(self, issue_key: str) -> dict[str, Any]:
        async with self._client() as client:
            resp = await client.get(f"/rest/api/3/issue/{issue_key}")
            self._raise_for_status(resp)
            return resp.json()

    async def search_issues(self, jql: str, fields: list[str] | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"jql": jql, "maxResults": 50}
        if fields:
            params["fields"] = ",".join(fields)
        async with self._client() as client:
            resp = await client.get("/rest/api/3/search", params=params)
            self._raise_for_status(resp)
            return resp.json().get("issues", [])

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            raise JiraError(resp.status_code, resp.text[:200])
