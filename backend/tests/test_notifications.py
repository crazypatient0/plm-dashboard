"""Tests for notification services (Teams + DingTalk)."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from src.notifications.dingtalk import send_dingtalk_message
from src.notifications.teams import send_teams_message

# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

class TestTeamsNotification:
    def test_sends_successfully(self) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_resp

        result = send_teams_message(
            "https://teams.example.com/webhook",
            "Test Title",
            "Test body",
            _client=mock_client,
        )
        assert result is True

        # Verify payload structure
        _, kwargs = mock_client.post.call_args
        payload = kwargs["json"]
        assert payload["@type"] == "MessageCard"
        assert payload["title"] == "Test Title"
        assert payload["text"] == "Test body"

    def test_http_error_returns_false(self) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_resp,
        )
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_resp

        result = send_teams_message(
            "https://teams.example.com/webhook",
            "Title",
            "Body",
            _client=mock_client,
        )
        assert result is False

    def test_network_error_returns_false(self) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.side_effect = httpx.RequestError("Connection failed")

        result = send_teams_message(
            "https://teams.example.com/webhook",
            "Title",
            "Body",
            _client=mock_client,
        )
        assert result is False


# ---------------------------------------------------------------------------
# DingTalk
# ---------------------------------------------------------------------------

class TestDingTalkNotification:
    def test_sends_successfully(self) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_resp

        result = send_dingtalk_message(
            "https://dingtalk.example.com/robot",
            "Test Title",
            "**bold** markdown body",
            _client=mock_client,
        )
        assert result is True

        # Verify payload structure
        _, kwargs = mock_client.post.call_args
        payload = kwargs["json"]
        assert payload["msgtype"] == "markdown"
        assert payload["markdown"]["title"] == "Test Title"
        assert payload["markdown"]["text"] == "**bold** markdown body"

    def test_api_error_code_returns_false(self) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"errcode": 400, "errmsg": "invalid token"}
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_resp

        result = send_dingtalk_message(
            "https://dingtalk.example.com/robot",
            "Title",
            "Body",
            _client=mock_client,
        )
        assert result is False

    def test_http_error_returns_false(self) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=mock_resp,
        )
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_resp

        result = send_dingtalk_message(
            "https://dingtalk.example.com/robot",
            "Title",
            "Body",
            _client=mock_client,
        )
        assert result is False

    def test_network_error_returns_false(self) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.side_effect = httpx.RequestError("Timeout")

        result = send_dingtalk_message(
            "https://dingtalk.example.com/robot",
            "Title",
            "Body",
            _client=mock_client,
        )
        assert result is False
