import os
import json
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

    ctx = {
        "items": items,
        "grouped": grouped,
        "categories": [c for c in cats if grouped[c]],
        "fx": fx or {},
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    html = digest_tpl.render(**ctx)

    digest_path = os.path.join(out_dir, "digests", f"{date_str}.html")
    with open(digest_path, "w", encoding="utf-8") as f:
        f.write(html)

    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_tpl.render(latest_date=date_str, items=items, grouped=grouped, categories=[c for c in cats if grouped[c]], fx=fx or {}, generated_at=ctx["generated_at"]))

    with open(os.path.join(out_dir, "digest.json"), "w", encoding="utf-8") as f:
        json.dump({"date": date_str, "fx": fx or {}, "items": items}, f, ensure_ascii=False, indent=2)

    return digest_path
