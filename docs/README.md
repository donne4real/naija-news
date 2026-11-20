# Naija News Digest — Documentation

Naija News Digest is a **daily, automated roundup of the top Nigerian news stories**. Every day it pulls headlines from the major Nigerian news sites, removes duplicates, ranks the most important stories, summarizes them with an AI model, and publishes a clean, ad-free page (plus an optional email newsletter).

**Site:** https://naija-news.pages.dev · **Code:** github.com/donne4real/naija-news (public) · **Running cost:** ~$0 (free tiers)

## Which guide do I need?

| If you are… | Read | It covers |
|---|---|---|
| **A reader** | [User guide](user-guide.md) | How to read the digest, sections, exchange rates, archive, subscribing |
| **The owner** | [Owner's guide](owner-guide.md) | How it runs by itself, accounts and keys, adding subscribers, costs, troubleshooting |
| **A developer** (or an AI assistant) maintaining it | [Developer guide](developer-guide.md) | Architecture, sources, pipeline, ranking, LLM providers, deployment, security |

## The one-minute version

```
Every day, 01:00 UTC (≈ 08:00/09:00 pm Virginia, ≈ 02:00 Lagos next day)
┌──────────────────────────────────────────────────────────────┐
│ GitHub Actions: .github/workflows/digest.yml                 │
│  1. fetch RSS from ~13 Nigerian news sites                    │
│  2. dedup by title similarity; filter stories already used   │
│  3. rank by cross-source coverage + recency                  │
│  4. fetch article text; summarize top stories with an LLM     │
│     (Anthropic Claude Haiku → Gemini Flash fallback)          │
│  5. assign a category (Politics, National, Sports, …)        │
│  6. fetch USD/GBP/EUR → NGN exchange rates                   │
│  7. render static HTML + JSON + archive page                 │
│  8. post to Beehiiv (email newsletter) — Resend fallback     │
│  9. commit new digest to the repo (archive)                  │
│ 10. deploy to Cloudflare Pages                               │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
                    Cloudflare Pages ──► you (and subscribers)
```

- **RSS feeds** from Punch, Vanguard, Premium Times, ThisDay, Daily Trust, Channels TV, BusinessDay, Leadership, Tribune, NAN, TechCabal, Nairametrics, Complete Sports supply the headlines.
- **Anthropic Claude Haiku** writes the summaries; **Gemini Flash** is the automatic fallback.
- **Beehiiv** distributes the email newsletter and handles subscribers/monetization; **Resend** is the fallback sender.
- Every day's digest is kept forever in `public/digests/`, so the archive grows automatically.
- A `published.json` file prevents the same story from appearing twice across days.

## Other documents

- Project README (quick setup): [`../README.md`](../README.md)
- Roadmap / planned work: [`../ROADMAP.md`](../ROADMAP.md)
- Design notes (LLM provider, fallback, tuning) are captured in the source and `.env.example`.

*Documentation written November 2026.*
