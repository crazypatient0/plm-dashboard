"""DingTalk (钉钉) notification service via Custom Robot Webhook.

Sends Markdown-formatted messages through a DingTalk custom robot.
See: https://open.dingtalk.com/document/robots/custom-robot-access
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


def send_dingtalk_message(
    webhook_url: str,
    title: str,
    message: str,
    *,
    _client: httpx.Client | None = None,
) -> bool:
    """Send a Markdown message to a DingTalk custom robot webhook.

    Parameters
    ----------
    webhook_url:
        The full DingTalk webhook URL (with access_token).
    title:
        Message title (shown in notification).
    message:
        Markdown body text.
    _client:
        Internal: injectable HTTP client for testing.

    Returns
    -------
    ``True`` on success, ``False`` on any failure (logged).
    """
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": message,
        },
    }

    client = _client or httpx.Client(timeout=10.0)

    try:
        resp = client.post(webhook_url, json=payload)
        resp.raise_for_status()
        # DingTalk returns {"errcode":0,"errmsg":"ok"} on success
        body = resp.json()
        if body.get("errcode") != 0:
            logger.error(
                "DingTalk API error: %s — %s",
                body.get("errcode"),
                body.get("errmsg", ""),
            )
            return False
        logger.info("DingTalk message sent: %s", title)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "DingTalk webhook responded %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        return False
    except httpx.RequestError as exc:
        logger.error("DingTalk webhook request failed: %s", exc)
        return False
    finally:
        if _client is None:
            client.close()
