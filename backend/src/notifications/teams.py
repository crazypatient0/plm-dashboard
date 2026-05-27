"""Microsoft Teams notification service via Incoming Webhook.

Sends simple MessageCard-formatted messages through a Teams channel
webhook URL. See: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

MESSAGE_CARD_TEMPLATE = {
    "@type": "MessageCard",
    "@context": "http://schema.org/extensions",
    "themeColor": "0076D7",
}


def send_teams_message(
    webhook_url: str,
    title: str,
    message: str,
    *,
    _client: httpx.Client | None = None,
) -> bool:
    """Send a MessageCard to a Teams Incoming Webhook URL.

    Parameters
    ----------
    webhook_url:
        The full Teams webhook URL (from channel Connectors).
    title:
        Card title (bold heading).
    message:
        Card text body.
    _client:
        Internal: injectable HTTP client for testing.

    Returns
    -------
    ``True`` on success, ``False`` on any failure (logged).
    """
    card = {
        **MESSAGE_CARD_TEMPLATE,
        "title": title,
        "text": message,
    }

    client = _client or httpx.Client(timeout=10.0)

    try:
        resp = client.post(webhook_url, json=card)
        resp.raise_for_status()
        logger.info("Teams message sent: %s", title)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Teams webhook responded %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        return False
    except httpx.RequestError as exc:
        logger.error("Teams webhook request failed: %s", exc)
        return False
    finally:
        if _client is None:
            client.close()
