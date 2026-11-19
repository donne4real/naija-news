import os
import httpx


def send_resend(items, date_str):
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return False
    to_raw = os.getenv("RESEND_TO", "")
    recipients = [x.strip() for x in to_raw.split(",") if x.strip()]
    if not recipients:
        return False
    frm = os.getenv("RESEND_FROM", "Naija News <digest@example.com>")
    parts = [f"<h2>Naija News Digest — {date_str}</h2>"]
    for it in items:
        parts.append(f"<h3>{it['title']}</h3>")
        parts.append(f"<p><em>{', '.join(it['sources'])}</em></p>")
        parts.append(f"<p>{it['summary']}</p>")
        if it.get("why"):
            parts.append(f"<p><strong>Why it matters:</strong> {it['why']}</p>")
        parts.append(f"<p><a href='{it['link']}'>Read more</a></p>")
    html = "\n".join(parts)
    try:
        r = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"from": frm, "to": recipients, "subject": f"Naija News Digest — {date_str}", "html": html},
            timeout=30,
        )
        r.raise_for_status()
        print("[publish] resend sent")
        return True
    except Exception as e:
        print(f"[publish] resend failed: {e}")
        return False


def publish_all(items, date_str):
    send_resend(items, date_str)
