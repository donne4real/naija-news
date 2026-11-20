import os
import re
from datetime import datetime, timezone

STOP = set("the a an and or of in to for on at with by is are was were be been being this that these those from as it its".split())


def _tokens(title):
    t = re.sub(r"[^a-z0-9 ]", " ", (title or "").lower())
    return set(w for w in t.split() if len(w) > 2 and w not in STOP)


def _sim(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def dedup(items, threshold=None):
    if threshold is None:
        threshold = float(os.getenv('DEDUP_THRESHOLD', '0.45'))
    stories = []
    for it in items:
        toks = _tokens(it["title"])
        best = None
        best_score = 0.0
        for st in stories:
            s = _sim(toks, st["_tokens"])
            if s > best_score:
                best_score = s
                best = st
        if best is not None and best_score >= threshold:
            best["items"].append(it)
            best["sources"].append(it["source"])
            if it["published"] < best["published"]:
                best["published"] = it["published"]
                best["title"] = it["title"]
                best["link"] = it["link"]
            if it["summary"] and it["summary"] not in best["snippets"]:
                best["snippets"].append(it["summary"])
        else:
            stories.append({
                "title": it["title"],
                "link": it["link"],
                "published": it["published"],
                "sources": [it["source"]],
                "snippets": [it["summary"]] if it["summary"] else [],
                "items": [it],
                "_tokens": toks,
            })
    for st in stories:
        st["sources"] = sorted(set(st["sources"]))
        del st["_tokens"]
    return stories


def rank(stories, top_n=5):
    now = datetime.now(timezone.utc)
    def score(s):
        hours = max((now - s["published"]).total_seconds() / 3600.0, 0)
        recency = max(0, 48 - hours) / 48.0
        return len(s["sources"]) * 2 + recency
    stories.sort(key=score, reverse=True)
    return stories[:top_n]
