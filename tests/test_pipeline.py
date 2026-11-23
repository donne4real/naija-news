"""Unit tests for Naija News Digest pipeline (dedup, rank, summarize, render, publish)."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from src import dedup, publish, render, summarize


def _make_item(title, source, link, hours_ago=1, summary="Sample summary text."):
    return {
        "title": title,
        "source": source,
        "link": link,
        "published": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        "summary": summary,
    }


def test_dedup_merges_similar_headlines_and_tracks_sources():
    items = [
        _make_item("CBN raises benchmark interest rate to combat inflation", "Punch", "https://punch.ng/1", hours_ago=2),
        _make_item("CBN raises benchmark interest rate to combat inflation in Nigeria", "Vanguard", "https://vanguard.ng/1", hours_ago=1),
        _make_item("Super Eagles qualify for AFCON knockout stage", "Channels", "https://channels.tv/2", hours_ago=1),
    ]
    stories = dedup.dedup(items, threshold=0.45)
    assert len(stories) == 2
    cbn = next(s for s in stories if "CBN" in s["title"])
    assert cbn["sources"] == ["Punch", "Vanguard"]
    assert cbn["link"] == "https://punch.ng/1"  # keeps earliest published


def test_rank_prioritizes_multi_source_and_recent():
    now = datetime.now(timezone.utc)
    stories = [
        {"title": "Old Single", "sources": ["A"], "published": now - timedelta(hours=40)},
        {"title": "Multi Source", "sources": ["A", "B", "C"], "published": now - timedelta(hours=5)},
        {"title": "Fresh Single", "sources": ["A"], "published": now - timedelta(hours=1)},
    ]
    ranked = dedup.rank(stories, top_n=2)
    assert ranked[0]["title"] == "Multi Source"
    assert ranked[1]["title"] == "Fresh Single"


def test_summarize_helpers_and_offline_fallback():
    assert summarize._norm_cat("business") == "Business"
    assert summarize._norm_cat("tech") == "Technology"
    assert summarize._norm_cat("unknown-xyz") == "National"

    assert summarize._needs_retry("Too short") is True
    assert summarize._needs_retry("A long enough sentence that still says read more at the end of it all.") is True
    assert summarize._needs_retry("Nigeria's central bank kept interest rates steady on Tuesday to stabilize the naira and curb inflation pressures.") is False

    now = datetime.now(timezone.utc)
    raw = [
        {
            "title": "Lagos rail line opens new station",
            "sources": ["Punch"],
            "link": "https://punch.ng/rail",
            "published": now,
            "snippets": ["The Lagos Red Line expanded commuter capacity across the mainland corridor."],
        }
    ]
    out = summarize._fallback(raw)
    assert len(out) == 1
    assert out[0]["category"] == "National"
    assert "Lagos Red Line" in out[0]["summary"]


def test_render_all_generates_html_json_search_and_rss(tmp_path):
    items = [
        {
            "title": "Naira stabilizes at official window",
            "sources": ["BusinessDay", "Punch"],
            "link": "https://businessday.ng/naira",
            "published": "2026-11-23T01:00:00+00:00",
            "summary": "The naira traded steadily after improved FX liquidity inflows.",
            "why": "Lower FX volatility eases import costs for businesses.",
            "category": "Business",
        },
        {
            "title": "TechCabal reports fintech funding rebound",
            "sources": ["TechCabal"],
            "link": "https://techcabal.com/fintech",
            "published": "2026-11-23T01:00:00+00:00",
            "summary": "Nigerian fintech startups closed fresh seed and Series A rounds.",
            "why": "Signals renewed investor confidence in local payments infrastructure.",
            "category": "Technology",
        },
    ]
    fx = {"usd": 1550.25, "gbp": 1980.10, "eur": 1690.50}
    render.render_all(items, "2026-11-23", str(tmp_path), fx=fx)

    assert (tmp_path / "index.html").is_file()
    assert (tmp_path / "archive.html").is_file()
    assert (tmp_path / "digests" / "2026-11-23.html").is_file()
    assert (tmp_path / "digests" / "2026-11-23.json").is_file()

    digest_json = json.loads((tmp_path / "digest.json").read_text(encoding="utf-8"))
    assert digest_json["date"] == "2026-11-23"
    assert len(digest_json["items"]) == 2

    search_idx = json.loads((tmp_path / "search-index.json").read_text(encoding="utf-8"))
    assert len(search_idx) == 2

    rss_xml = (tmp_path / "feed.xml").read_text(encoding="utf-8")
    assert "<rss version=\"2.0\">" in rss_xml
    assert "Naija News Digest — 2026-11-23" in rss_xml


def test_publish_html_and_resend_mock(monkeypatch):
    items = [
        {
            "title": "Headline One",
            "sources": ["Punch"],
            "link": "https://punch.ng/1",
            "summary": "Concise summary of the top Nigerian story.",
            "why": "Impacts households nationwide.",
            "category": "National",
        }
    ]
    html = publish._build_html(items, "2026-11-23", {"usd": 1550.0, "gbp": 1950.0, "eur": 1680.0})
    assert "Naija News Digest" in html
    assert "1550.00" in html
    assert "Headline One" in html

    # Unconfigured returns False cleanly
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("BEEHIIV_API_KEY", raising=False)
    assert publish.send_resend(items, "2026-11-23") is False

    # Configured sends expected payload
    monkeypatch.setenv("RESEND_API_KEY", "re_test_12345")
    monkeypatch.setenv("RESEND_TO", "reader@example.com")
    monkeypatch.setenv("RESEND_FROM", "Naija News <digest@example.com>")
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    with patch("httpx.post", return_value=mock_resp) as mock_post:
        assert publish.send_resend(items, "2026-11-23") is True
        assert mock_post.call_count == 1
        sent_json = mock_post.call_args.kwargs["json"]
        assert sent_json["to"] == ["reader@example.com"]
        assert "2026-11-23" in sent_json["subject"]
