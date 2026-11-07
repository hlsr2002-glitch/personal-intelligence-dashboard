"""Small, side-effect-limited ntfy publisher for the dashboard."""

from __future__ import annotations

import re
import urllib.error
import urllib.request


_SLUG = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_NTFY_URL = re.compile(r"^(?:https?://)?ntfy\.sh/([A-Za-z0-9_-]{1,64})/?$")


def normalize_topic(value: str | None) -> str | None:
    """Accept either a topic slug or the common ntfy.sh/topic URL form."""
    if not value:
        return None
    candidate = value.strip()
    match = _NTFY_URL.fullmatch(candidate)
    if match:
        return match.group(1)
    return candidate if _SLUG.fullmatch(candidate) else None


def _publish(topic_value: str | None, title: str, message: str, priority: str = "default") -> bool:
    topic = normalize_topic(topic_value)
    if not topic:
        return False
    request = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=message.encode("utf-8"),
        method="POST",
        headers={
            "Title": title,
            "Priority": priority,
            "Content-Type": "text/plain; charset=utf-8",
            "User-Agent": "PersonalIntelligenceDashboard/2.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError):
        return False


def send_alert_notifications(topic: str | None, alerts: list[dict[str, str]]) -> int:
    """Publish only newly active financial alerts; return number accepted."""
    sent = 0
    for alert in alerts:
        if _publish(topic, alert["title"], alert["detail"], "high"):
            sent += 1
    return sent


def send_test_notification(topic: str | None) -> bool:
    """Send a neutral test message without reading or changing alert state."""
    return _publish(
        topic,
        "Teste de notificações",
        "Canal ntfy do dashboard ligado. Esta mensagem não representa um alerta financeiro.",
        "default",
    )
