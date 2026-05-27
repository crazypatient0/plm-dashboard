"""Tests for the PLM HTTP client with mocked httpx."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.plm_client import PlmAuthError, PlmClient, PlmConnectionError


@pytest.fixture
def client() -> PlmClient:
    return PlmClient(
        base_url="https://plm.example.com",
        username="test_user",
        password="test_pass",
    )


class TestInit:
    def test_strips_trailing_slash(self) -> None:
        c = PlmClient("https://plm.example.com/", "u", "p")
        assert c.base_url == "https://plm.example.com"

    def test_verify_false_by_default(self) -> None:
        """Client is constructed with verify=False (no SSL errors on creation)."""
        c = PlmClient("https://plm.example.com", "u", "p")
        assert c.base_url == "https://plm.example.com"
        assert c.username == "u"


class TestLogin:
    def test_success_flow(self, client: PlmClient) -> None:
        """Three-step login: GET /login -> POST /login -> GET /dashboard."""
        mock_responses = [
            MagicMock(spec=httpx.Response, status_code=200),
            MagicMock(spec=httpx.Response, status_code=200),
            MagicMock(
                spec=httpx.Response,
                status_code=200,
                cookies={"CSRFToken": "abc123"},
            ),
        ]

        with patch.object(client._client, "get") as mock_get, patch.object(
            client._client, "post"
        ) as mock_post:
            mock_get.side_effect = mock_responses[0:3:2]  # calls 1 and 3
            mock_post.return_value = mock_responses[1]

            result = client.login()

            # Verify step 1
            mock_get.assert_any_call("https://plm.example.com/login")
            # Verify step 2: form data
            mock_post.assert_called_once_with(
                "https://plm.example.com/login?skip-sso=1",
                data={
                    "step": "auth",
                    "username": "test_user",
                    "password": "test_pass",
                    "remember": "true",
                    "query": "",
                    "acr_values": "",
                },
            )
            # Verify step 3
            mock_get.assert_any_call("https://plm.example.com/dashboard")

            assert result is client
            assert client._is_logged_in is True
            assert client._client.headers["X-CSRF-Token"] == "abc123"

    def test_step1_get_fails_raises_auth_error(self, client: PlmClient) -> None:
        mock_get = MagicMock()
        mock_get.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=MagicMock(status_code=401)
        )

        with patch.object(client._client, "get", mock_get):
            with pytest.raises(PlmAuthError, match="Login failed with status 401"):
                client.login()

    def test_network_error_raises_connection_error(
        self, client: PlmClient
    ) -> None:
        mock_get = MagicMock()
        mock_get.side_effect = httpx.RequestError("DNS failure")

        with patch.object(client._client, "get", mock_get):
            with pytest.raises(
                PlmConnectionError, match="Unable to connect to"
            ):
                client.login()

    def test_no_csrf_token_raises_auth_error(self, client: PlmClient) -> None:
        mock_responses = [
            MagicMock(spec=httpx.Response, status_code=200),
            MagicMock(spec=httpx.Response, status_code=200),
            MagicMock(
                spec=httpx.Response,
                status_code=200,
                cookies={},  # No CSRFToken
            ),
        ]

        with patch.object(client._client, "get") as mock_get, patch.object(
            client._client, "post"
        ) as mock_post:
            mock_get.side_effect = mock_responses[0:3:2]
            mock_post.return_value = mock_responses[1]

            with pytest.raises(
                PlmAuthError, match="Login succeeded but no CSRFToken"
            ):
                client.login()


class TestSearch:
    def test_basic_search(self, client: PlmClient) -> None:
        expected_data = {"data": {"rows": [{"columns": ["val1"]}]}}
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = expected_data

        client._is_logged_in = True
        client._client.headers["X-CSRF-Token"] = "abc123"

        with patch.object(client._client, "post", return_value=mock_resp):
            results = client.search(
                "/class/part/CDB_Search/run",
                {"teile_stamm.share_status": "=9"},
            )

        assert len(results) == 1
        assert results[0]["columns"] == ["val1"]

    def test_search_auto_reconnect_on_403(self, client: PlmClient) -> None:
        """Should re-login once on 403 and retry the search."""
        fail_resp = MagicMock(spec=httpx.Response)
        fail_resp.status_code = 403

        success_resp = MagicMock(spec=httpx.Response)
        success_resp.status_code = 200
        success_resp.json.return_value = {
            "data": {"rows": [{"columns": ["retried"]}]}
        }

        client._is_logged_in = False

        with patch.object(client._client, "post") as mock_post, patch.object(
            client, "login"
        ) as mock_login:
            mock_post.side_effect = [fail_resp, success_resp]

            results = client.search("/class/part/CDB_Search/run", {})

            assert len(results) == 1
            assert results[0]["columns"] == ["retried"]
            assert mock_post.call_count == 2
            mock_login.assert_called_once()

    def test_search_auto_reconnect_on_401(self, client: PlmClient) -> None:
        fail_resp = MagicMock(spec=httpx.Response)
        fail_resp.status_code = 401

        success_resp = MagicMock(spec=httpx.Response)
        success_resp.status_code = 200
        success_resp.json.return_value = {"rows": [{"columns": ["retried"]}]}

        with patch.object(client._client, "post") as mock_post, patch.object(
            client, "login"
        ) as mock_login:
            mock_post.side_effect = [fail_resp, success_resp]

            results = client.search("/class/part/CDB_Search/run", {})

            assert len(results) == 1
            mock_login.assert_called_once()

    def test_search_reconnect_twice_fails(self, client: PlmClient) -> None:
        """Two consecutive 403s -- first triggers re-login, second raises."""
        fail_resp = MagicMock(spec=httpx.Response)
        fail_resp.status_code = 403

        with patch.object(client._client, "post", return_value=fail_resp), patch.object(
            client, "login", return_value=None
        ):
            with pytest.raises(
                PlmAuthError, match="Re-authentication failed during search retry"
            ):
                client.search("/class/part/CDB_Search/run", {})

    def test_network_error_during_search(self, client: PlmClient) -> None:
        with patch.object(client._client, "post") as mock_post:
            mock_post.side_effect = httpx.RequestError("timeout")

            with pytest.raises(
                PlmConnectionError, match="Search request failed"
            ):
                client.search("/class/part/CDB_Search/run", {})

    def test_search_returns_empty_list_on_missing_keys(
        self, client: PlmClient
    ) -> None:
        """When data/rows keys are absent, return an empty list."""
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}

        with patch.object(client._client, "post", return_value=mock_resp):
            results = client.search("/class/part/CDB_Search/run", {})
            assert results == []


class TestConvenienceMethods:
    def test_search_parts(self, client: PlmClient) -> None:
        with patch.object(client, "search", return_value=[{"id": 1}]) as mock_search:
            result = client.search_parts()
            assert result == [{"id": 1}]
            mock_search.assert_called_once_with(
                "/class/part/CDB_Search/run",
                {"teile_stamm.share_status": "=2 or =3 or =9 or =11"},
            )

    def test_search_documents(self, client: PlmClient) -> None:
        with patch.object(client, "search", return_value=[{"id": 2}]) as mock_search:
            result = client.search_documents()
            assert result == [{"id": 2}]
            mock_search.assert_called_once_with(
                "/class/document/CDB_Search/run",
                {
                    "zeichnung.share_status": "=2 or =3 or =9 or =11",
                    "zeichnung.cdb_obsolete": "0",
                },
            )

    def test_search_conversion(self, client: PlmClient) -> None:
        with patch.object(client, "search", return_value=[{"id": 3}]) as mock_search:
            result = client.search_conversion()
            assert result == [{"id": 3}]
            mock_search.assert_called_once_with(
                "/class/conversion/CDB_Search/run",
                {"conversion.cdbmq_site": "edgeNiChina"},
            )


class TestSessionStatus:
    def test_active_session(self, client: PlmClient) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200

        with patch.object(client._client, "get", return_value=mock_resp):
            assert client.get_session_status() is True

    def test_inactive_session(self, client: PlmClient) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 302

        with patch.object(client._client, "get", return_value=mock_resp):
            assert client.get_session_status() is False

    def test_network_error(self, client: PlmClient) -> None:
        with patch.object(client._client, "get") as mock_get:
            mock_get.side_effect = httpx.RequestError("timeout")
            assert client.get_session_status() is False


class TestContextManager:
    def test_close_on_exit(self, client: PlmClient) -> None:
        with patch.object(client._client, "close") as mock_close:
            with client:
                pass
            mock_close.assert_called_once()
