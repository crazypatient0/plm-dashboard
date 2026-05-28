"""PLM client module for PIA PLM (ARAS Innovator v15.x).

Provides login, session management, and search operations against
the PLM system at piaplmp.piagad.com.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.exceptions import PlmApiError, PlmAuthError, PlmConnectionError

logger = logging.getLogger(__name__)


class PlmClient:
    """HTTP client for interacting with the PIA PLM system.

    Handles the ARAS Innovator form-based authentication flow including
    CSRF token extraction and automatic session reconnection on expiry.
    """

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._is_logged_in = False
        self._client = httpx.Client(timeout=30.0, verify=False, follow_redirects=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def login(self) -> PlmClient:
        """Execute the ARAS Innovator three-step login flow.

        Steps:
          1. GET /login        -- establishes session, gets session cookie
          2. POST /login?skip-sso=1 -- submits credentials as form data
          3. GET /dashboard    -- confirms successful authentication

        On success the ``X-CSRF-Token`` header is set on the internal
        client for all subsequent requests.
        """
        try:
            # Step 1 -- obtain session cookie
            resp1 = self._client.get(f"{self.base_url}/login")
            resp1.raise_for_status()

            # Step 2 -- submit credentials
            form = {
                "step": "auth",
                "username": self.username,
                "password": self.password,
                "remember": "true",
                "query": "",
                "acr_values": "",
            }
            resp2 = self._client.post(
                f"{self.base_url}/login?skip-sso=1",
                data=form,
            )
            if resp2.status_code not in (200, 303):
                resp2.raise_for_status()

            # Step 3 -- confirm dashboard access
            resp3 = self._client.get(f"{self.base_url}/dashboard")
            resp3.raise_for_status()

            # Extract CSRF token from response cookies
            csrf_token = resp3.cookies.get("CSRFToken")
            if not csrf_token:
                raise PlmAuthError(
                    "Login succeeded but no CSRFToken cookie was returned"
                )

            self._client.headers["X-CSRF-Token"] = csrf_token
            self._is_logged_in = True
            logger.info("Successfully logged into PLM at %s", self.base_url)
            return self

        except httpx.HTTPStatusError as exc:
            raise PlmAuthError(
                f"Login failed with status {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise PlmConnectionError(
                f"Unable to connect to {self.base_url}: {exc}"
            ) from exc

    def search(self, endpoint_path: str, values: dict[str, str]) -> list[dict[str, Any]]:
        """Execute a search via the PLM internal UI-support operation endpoint.

        Parameters
        ----------
        endpoint_path:
            Path fragment identifying the search, e.g.
            ``"/class/part/CDB_Search/run"``.
        values:
            Key-value pairs of search criteria.

        Returns
        -------
        List of result rows, where each row is a dict with at least a
        ``"columns"`` key.
        """
        url = f"{self.base_url}/internal/uisupport/operation{endpoint_path}"
        payload: dict[str, Any] = {
            "object_navigation_id": None,
            "values": values,
        }

        for attempt in range(2):
            try:
                resp = self._client.post(
                    url,
                    json=payload,
                )
            except httpx.RequestError as exc:
                raise PlmConnectionError(f"Search request failed: {exc}") from exc

            # Auto-reconnect on 403 (session expired) or login redirect
            if resp.status_code in (401, 403):
                if attempt == 0:
                    logger.warning("Session expired, re-authenticating ...")
                    self.login()
                    continue
                raise PlmAuthError(
                    "Re-authentication failed during search retry"
                )

            resp.raise_for_status()
            data = resp.json()
            rows = data.get("data", {}).get("rows", data.get("rows", []))
            return list(rows)

        # Should not reach here, but satisfy the return type
        return []

    def search_parts(self) -> list[dict[str, Any]]:
        """Search for parts with active share status."""
        return self.search(
            "/class/part/CDB_Search/run",
            {"teile_stamm.share_status": "=2 or =3 or =9 or =11"},
        )

    def search_documents(self) -> list[dict[str, Any]]:
        """Search for documents that are shared and not obsolete."""
        return self.search(
            "/class/document/CDB_Search/run",
            {
                "zeichnung.share_status": "=2 or =3 or =9 or =11",
                "zeichnung.cdb_obsolete": "0",
            },
        )

    def search_conversion(self) -> list[dict[str, Any]]:
        """Search for MQ ACS records for the specified site."""
        return self.search(
            "/class/mq_acs/CDB_Search/run",
            {"mq_acs.cdbmq_site": "edgeNiChina"},
        )

    def get_session_status(self) -> bool:
        """Check whether the current session is still valid.

        Makes a lightweight request to the dashboard endpoint.
        """
        try:
            resp = self._client.get(f"{self.base_url}/dashboard")
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> PlmClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
