import re
import feedparser
import requests
from datetime import datetime, timezone
from dateutil import parser as dateparser

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _parse_date(entry):
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if val:
            try:
                dt = dateparser.parse(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            try:
                return datetime(*st[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def _clean_html(html):
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_source(src):
    items = []
    try:
        r = requests.get(src["url"], timeout=20, headers={"User-Agent": UA})
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        for e in feed.entries[:25]:
            items.append({
                "source": src["name"],
                "title": (e.get("title") or "").strip(),
                "link": (e.get("link") or "").strip(),
                "summary": _clean_html(e.get("summary") or e.get("description") or ""),
                "published": _parse_date(e),
            })
    except Exception as ex:
        print(f"[fetch] {src['name']} failed: {ex}")
    return items


def fetch_all(sources):
    out = []
    for s in sources:
        out.extend(fetch_source(s))
    return out
