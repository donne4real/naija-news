import os
import httpx

CATEGORIES = ["Politics", "National", "Sports", "Business", "Technology", "Other"]


def _group(items):
    g = {c: [] for c in CATEGORIES}
    for it in items:
        cat = it.get("category", "National")
        if cat not in g:
            cat = "National"
        g[cat].append(it)
    return g


def _build_html(items, date_str, fx):
    parts = []
    parts.append("<div style='font-family:system-ui,Arial,sans-serif;max-width:640px;margin:0 auto;padding:20px;color:#222'>")
    parts.append(f"<h1 style='color:#008751'>🇳🇬 Naija News Digest</h1>")
    parts.append(f"<p style='color:#666'>{date_str} &middot; Top stories by category</p>")

    if fx and fx.get("usd"):
        parts.append("<div style='background:#fff;border:1px solid #eee;border-radius:8px;padding:10px 14px;margin:12px 0;font-size:14px'>")
        parts.append(f"<b style='color:#008751'>USD/NGN:</b> {fx['usd']:.2f} &nbsp; ")
        if fx.get("gbp"):
            parts.append(f"<b style='color:#008751'>GBP/NGN:</b> {fx['gbp']:.2f} &nbsp; ")
        if fx.get("eur"):
            parts.append(f"<b style='color:#008751'>EUR/NGN:</b> {fx['eur']:.2f}")
        parts.append("</div>")

    g = _group(items)
    for cat in CATEGORIES:
        if not g[cat]:
            continue
        parts.append(f"<h2 style='color:#008751;border-bottom:2px solid #008751;padding-bottom:4px'>{cat}</h2>")
        for it in g[cat]:
            parts.append("<div style='background:#fff;border:1px solid #eee;border-radius:8px;padding:14px;margin:10px 0'>")
            parts.append(f"<h3 style='margin:0 0 6px;font-size:16px'>{it['title']}</h3>")
            parts.append(f"<div style='font-size:12px;color:#888;margin-bottom:8px'>{', '.join(it['sources'])}</div>")
            parts.append(f"<p style='line-height:1.6;margin:6px 0'>{it['summary']}</p>")
            if it.get("why"):
                parts.append(f"<div style='background:#eaf5ef;padding:8px 12px;border-left:4px solid #FFC107;margin:8px 0;font-size:14px'><b>Why it matters:</b> {it['why']}</div>")
            parts.append(f"<p style='margin:6px 0'><a href='{it['link']}' style='color:#008751'>Read original →</a></p>")
            parts.append("</div>")

    parts.append("<p style='font-size:12px;color:#888;margin-top:20px'>Naija News Digest · Automated daily roundup.</p>")
    parts.append("</div>")
    return "\n".join(parts)


def send_beehiiv(items, date_str, fx=None):
    api_key = os.getenv("BEEHIIV_API_KEY")
    pub_id = os.getenv("BEEHIIV_PUBLICATION_ID")
    if not api_key or not pub_id:
        return False
    html = _build_html(items, date_str, fx)
    url = f"https://api.beehiiv.com/v2/publications/{pub_id}/posts"
    payload = {
        "title": f"Naija News Digest — {date_str}",
        "subtitle": "Top stories by category",
        "body_content": html,
        "status": "confirmed",
    }
    try:
        r = httpx.post(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=60)
        r.raise_for_status()
        print("[publish] beehiiv post created")
        return True
    except Exception as e:
        print(f"[publish] beehiiv failed: {e}")
        try:
            print(r.text[:300])
        except Exception:
            pass
        return False


def send_resend(items, date_str, fx=None):
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return False
    to_raw = os.getenv("RESEND_TO", "")
    recipients = [x.strip() for x in to_raw.split(",") if x.strip()]
    if not recipients:
        return False
    frm = os.getenv("RESEND_FROM", "Naija News <digest@example.com>")
    html = _build_html(items, date_str, fx)
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


def publish_all(items, date_str, fx=None):
    if send_beehiiv(items, date_str, fx=fx):
        return
    if send_resend(items, date_str, fx=fx):
        return
    print("[publish] no email provider configured")