import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src import sites, fetch, dedup, enrich, summarize, render, publish

OUT_DIR = os.getenv("OUT_DIR", "public")


def main():
    print("[run] fetching feeds...")
    items = fetch.fetch_all(sites.SOURCES)
    print(f"[run] fetched {len(items)} raw items")

    stories = dedup.dedup(items)
    print(f"[run] {len(stories)} unique stories")

    top = dedup.rank(stories, top_n=5)
    print(f"[run] top {len(top)} selected")

    for s in top:
        s["article_text"] = enrich.fetch_article_text(s["link"])

    summarized = summarize.summarize(top)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(base, OUT_DIR)
    render.render_all(summarized, date_str, out_path)
    print(f"[run] rendered to {out_path}")

    publish.publish_all(summarized, date_str)
    print("[run] done")


if __name__ == "__main__":
    main()
