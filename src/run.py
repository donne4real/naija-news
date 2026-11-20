import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src import sites, fetch, dedup, enrich, summarize, render, publish, fx

OUT_DIR = os.getenv("OUT_DIR", "public")


def main():
    print("[run] fetching feeds...")
    items = fetch.fetch_all(sites.SOURCES)
    print(f"[run] fetched {len(items)} raw items")

    stories = dedup.dedup(items)
    print(f"[run] {len(stories)} unique stories")

    top = dedup.rank(stories, top_n=24)
    # ensure tech sources represented
    tech_sources = {"TechCabal"}
    tech_candidates = [s for s in stories if tech_sources & set(s["sources"])]
    tech_candidates.sort(key=lambda x: x["published"], reverse=True)
    # inject up to 3 tech stories if not already present
    existing_links = {s["link"] for s in top}
    injected = 0
    for tc in tech_candidates:
        if tc["link"] not in existing_links and injected < 3:
            top = top[:-1] + [tc]
            existing_links.add(tc["link"])
            injected += 1
    print(f"[run] top {len(top)} selected")

    for s in top:
        s["article_text"] = enrich.fetch_article_text(s["link"])

    summarized = summarize.summarize(top)

    # balance: up to 3 per category, cap 15
    cats = ["Politics", "National", "Sports", "Business", "Technology", "Other"]
    balanced = []
    counts = {c: 0 for c in cats}
    # first pass: take up to 3 from each category
    for cat in cats:
        for it in summarized:
            if it.get("category", "National") == cat and counts[cat] < 3 and len(balanced) < 15:
                balanced.append(it)
                counts[cat] += 1
    # second pass: fill remaining slots
    for it in summarized:
        if it not in balanced and len(balanced) < 15:
            balanced.append(it)
            c = it.get("category", "National")
            if c in counts:
                counts[c] += 1
    summarized = balanced
    print(f"[run] balanced to {len(summarized)} items: { {c:counts[c] for c in cats} }")

    rates = fx.get_rates()
    print(f"[run] fx: {rates}")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(base, OUT_DIR)
    render.render_all(summarized, date_str, out_path, fx=rates)
    print(f"[run] rendered to {out_path}")

    publish.publish_all(summarized, date_str, fx=rates)
    print("[run] done")


if __name__ == "__main__":
    main()
