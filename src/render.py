import os
import json
import html as _html
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader


def _env():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return Environment(loader=FileSystemLoader(os.path.join(base, "templates")), autoescape=True)


def render_all(items, date_str, out_dir, fx=None):
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "digests"), exist_ok=True)
    env = _env()
    digest_tpl = env.get_template("digest.html")
    index_tpl = env.get_template("index.html")

    # group by category in fixed order
    cats = ["Politics", "National", "Sports", "Business", "Technology", "Other"]
    grouped = {c: [] for c in cats}
    for it in items:
        cat = it.get("category", "National")
        if cat not in grouped:
            cat = "National"
        grouped[cat].append(it)

    # scan existing digests for archive (always include today's digest)
    digests_dir = os.path.join(out_dir, "digests")
    digests = []
    if os.path.isdir(digests_dir):
        digests = sorted([f.replace(".html","") for f in os.listdir(digests_dir) if f.endswith(".html")], reverse=True)
    if date_str not in digests:
        digests = sorted(digests + [date_str], reverse=True)

    ctx = {
        "items": items,
        "grouped": grouped,
        "categories": [c for c in cats if grouped[c]],
        "fx": fx or {},
        "subscribe_url": os.getenv("BEEHIIV_SUBSCRIBE_URL", ""),
        "date": date_str,
        "digests": digests,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    html = digest_tpl.render(**ctx)

    digest_path = os.path.join(out_dir, "digests", f"{date_str}.html")
    with open(digest_path, "w", encoding="utf-8") as f:
        f.write(html)

    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_tpl.render(latest_date=date_str, items=items, grouped=grouped, categories=[c for c in cats if grouped[c]], fx=fx or {}, digests=digests, subscribe_url=os.getenv("BEEHIIV_SUBSCRIBE_URL",""), generated_at=ctx["generated_at"]))

    # archive page
    archive_tpl = env.get_template("archive.html")
    with open(os.path.join(out_dir, "archive.html"), "w", encoding="utf-8") as f:
        f.write(archive_tpl.render(digests=digests, generated_at=ctx["generated_at"]))

    with open(os.path.join(out_dir, "digest.json"), "w", encoding="utf-8") as f:
        json.dump({"date": date_str, "fx": fx or {}, "items": items}, f, ensure_ascii=False, indent=2)

    # per-day json (for archive/search)
    with open(os.path.join(out_dir, "digests", f"{date_str}.json"), "w", encoding="utf-8") as f:
        json.dump({"date": date_str, "fx": fx or {}, "items": items}, f, ensure_ascii=False, indent=2)

    # build search index from all per-day json files
    search_items = []
    ddir = os.path.join(out_dir, "digests")
    if os.path.isdir(ddir):
        for fn in sorted(os.listdir(ddir)):
            if not fn.endswith(".json"):
                continue
            try:
                dd = json.load(open(os.path.join(ddir, fn), encoding="utf-8"))
            except Exception:
                continue
            for it in dd.get("items", []):
                search_items.append({
                    "date": dd.get("date", fn.replace(".json","")),
                    "title": it.get("title",""),
                    "summary": it.get("summary",""),
                    "category": it.get("category",""),
                    "sources": it.get("sources",[]),
                    "url": it.get("link",""),
                })
    with open(os.path.join(out_dir, "search-index.json"), "w", encoding="utf-8") as f:
        json.dump(search_items, f, ensure_ascii=False)

    # RSS feed: one item per daily digest (accumulated archive)
    rss_items = []
    for d in digests:
        desc_parts = []
        jpath = os.path.join(out_dir, "digests", f"{d}.json")
        if os.path.exists(jpath):
            try:
                dd = json.load(open(jpath, encoding="utf-8"))
                for it in dd.get("items", [])[:5]:
                    desc_parts.append(f"- {it.get('title','')}")
            except Exception:
                pass
        description = _html.escape("\n".join(desc_parts)) if desc_parts else f"Daily roundup for {d}"
        rss_items.append(f"""    <item>
      <title>Naija News Digest — {d}</title>
      <link>https://naija-news.pages.dev/digests/{d}.html</link>
      <guid isPermaLink="true">https://naija-news.pages.dev/digests/{d}.html</guid>
      <description>{description}</description>
      <pubDate>{d}T01:00:00Z</pubDate>
    </item>""")
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Naija News Digest</title>
    <link>https://naija-news.pages.dev/</link>
    <description>Daily roundup of top Nigerian news stories</description>
    <language>en</language>
    <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>
{chr(10).join(rss_items)}
  </channel>
</rss>"""
    with open(os.path.join(out_dir, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(rss)


    # search page
    search_tpl = env.get_template("search.html")
    with open(os.path.join(out_dir, "search.html"), "w", encoding="utf-8") as f:
        f.write(search_tpl.render(generated_at=ctx["generated_at"]))
