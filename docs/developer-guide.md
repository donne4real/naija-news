# Naija News Digest — Developer guide

Enough detail for a developer (or an AI assistant) to understand, maintain and extend Naija News Digest. The binding design is the roadmap and the source; this guide describes the system **as built**.

## 1. Architecture

```
                  ┌──────────────── GitHub Actions: .github/workflows/digest.yml ────────────────┐
  ~13 RSS feeds ─►│ pipeline (Python)                                                            │
  (Nigerian news) │   fetch.py → dedup.py → (tech injection) → enrich.py → summarize.py →         │
                  │   fx.py → render.py → publish.py                                             │
  LLM (Claude/   │        writes public/ ──► git commit (digests + published.json) ──► push     │
  Gemini) ───────►│        wrangler pages deploy ──► Cloudflare Pages                              │
                  └────────────────────────────────────────────────────────────────────────────────┘
                                                             Cloudflare Pages ──► browser
                                                             Beehiiv ──► subscribers' inboxes
```

- **No server, no database.** The pipeline writes static HTML/JSON files; the site is static.
- **State lives in git.** `public/digests/` and `published.json` are committed daily, so history is versioned.
- **Secrets never reach the browser.** Only the pipeline (in GitHub Actions) holds API keys.

## 2. Repository layout

```
naija-news/
├── .env / .env.example       local keys (git-ignored) / template
├── .github/workflows/
│   └── digest.yml            scheduled pipeline → commit → deploy
├── data/                     (reserved)
├── docs/                     this documentation
├── public/                   generated output (git-ignored except digests/)
│   ├── index.html            latest digest
│   ├── archive.html          list of past digests
│   ├── digest.json           latest digest as JSON
│   └── digests/YYYY-MM-DD.html   one file per day (committed)
├── published.json            set of featured story links (committed, prevents repeats)
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── sites.py              RSS source list
│   ├── fetch.py              fetch + parse RSS feeds
│   ├── dedup.py              title-similarity clustering + ranking
│   ├── enrich.py             fetch article text from each link
│   ├── summarize.py          LLM summarization + category assignment (provider-agnostic)
│   ├── fx.py                 USD/GBP/EUR → NGN exchange rates
│   ├── render.py             Jinja2 rendering (index, digest, archive)
│   ├── publish.py            Beehiiv (primary) + Resend (fallback) email
│   └── run.py                orchestrator
├── templates/
│   ├── digest.html           per-day digest template
│   ├── index.html            latest digest template
│   └── archive.html          archive index template
└── ROADMAP.md
```

## 3. Data sources

### RSS feeds (`src/sites.py`)
~13 Nigerian news sites. Each entry: `{"name": ..., "url": ...}`. `fetch.py` uses `feedparser` + `requests` with a browser User-Agent. Failed feeds are logged and skipped (never fail the run).

### LLM summarization (`src/summarize.py`)
- Provider-agnostic OpenAI-compatible client. Supported: `openai`, `groq`, `openrouter`, `mistral`, `deepseek`, `gemini`, `anthropic`, `together`.
- Resolution order: `LLM_PROVIDER` → env-specific key → generic `LLM_API_KEY` → `LLM_BASE_URL`/`LLM_MODEL` overrides.
- Automatic fallback: primary → `LLM_FALLBACK_PROVIDER` → RSS snippets.
- Anthropic returns JSON wrapped in markdown fences; the code strips them before `json.loads`.
- Prompt asks for `summary`, `why`, and `category` (Politics/National/Sports/Business/Technology/Other).

### Exchange rates (`src/fx.py`)
`https://open.er-api.com/v6/latest/USD` — free, no key. Computes NGN per USD/GBP/EUR.

### Email (`src/publish.py`)
- Beehiiv: `POST /v2/publications/{id}/posts` with `body_content` (HTML). Status `confirmed` (publishes/sends immediately).
- Resend: `POST /emails` with the same HTML. Used only if Beehiiv keys are missing or fail.

## 4. Pipeline (`src/run.py`)

1. Compute `date_str` (UTC). **Skip** if `public/digests/{date}.html` exists (unless `FORCE_RUN=1`).
2. Fetch all RSS feeds → raw items.
3. `dedup.dedup()` clusters by title similarity (threshold `DEDUP_THRESHOLD`).
4. Filter out links already in `published.json` (prevents repeats across days).
5. `dedup.rank()` scores by `len(sources)*RANK_SOURCE_WEIGHT + recency` (recency window `RANK_RECENCY_HOURS`), takes `TOP_N`.
6. Inject up to 3 TechCabal stories (to guarantee a Technology section).
7. `enrich.fetch_article_text()` fetches article text for each candidate.
8. `summarize.summarize()` calls the LLM; falls back to snippets.
9. Balance into categories (up to `MAX_PER_CATEGORY` each, total `DIGEST_SIZE`).
10. Record new links in `published.json`.
11. `fx.get_rates()`.
12. `render.render_all()` writes `index.html`, `digests/{date}.html`, `archive.html`, `digest.json`.
13. `publish.publish_all()` posts to Beehiiv (or Resend).
14. Deploy (via workflow) to Cloudflare Pages.

## 5. Dedup & ranking (`src/dedup.py`)

- `_tokens()`: lowercase, strip punctuation, drop stopwords, drop words ≤2 chars.
- `_sim()`: Jaccard similarity of token sets.
- `dedup()`: greedy clustering; an item joins an existing cluster if similarity ≥ threshold; otherwise starts a new cluster. Each cluster tracks sources, snippets, earliest published date.
- `rank()`: score = `len(sources) * source_weight + recency` where recency ∈ [0,1] over `recency_hours`. Sorts descending, returns top N.

## 6. Rendering (`src/render.py`)

- Jinja2 templates in `templates/`.
- `render_all(items, date_str, out_dir, fx)`:
  - Groups items by category in fixed order.
  - Scans `out_dir/digests/` for existing `*.html` to build the archive list.
  - Writes `index.html` (latest), `digests/{date}.html`, `archive.html`, `digest.json`.
- Templates use a Nigerian green/gold theme (`#008751`, `#FFC107`).
- `feed.xml` is a daily-roundup archive feed: one `<item>` per archived digest (newest first), linking to that day's page.

## 7. Configuration (env vars)

See `.env.example`. Key groups:

- **LLM:** `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_FALLBACK_PROVIDER`, `LLM_FALLBACK_MODEL`, plus provider-specific keys.
- **Email:** `BEEHIIV_API_KEY`, `BEEHIIV_PUBLICATION_ID`, `BEEHIIV_SUBSCRIBE_URL`, `RESEND_API_KEY`, `RESEND_FROM`, `RESEND_TO`.
- **Cloudflare:** `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `PAGES_PROJECT_NAME`.
- **Tuning:** `DEDUP_THRESHOLD`, `RANK_SOURCE_WEIGHT`, `RANK_RECENCY_HOURS`, `TOP_N`, `DIGEST_SIZE`, `MAX_PER_CATEGORY`.
- **Control:** `FORCE_RUN`, `OUT_DIR`.

## 8. Deployment

- **Manual (local):** `python3 -m src.run` then `npx wrangler pages deploy public --project-name=naija-news --branch=main`.
- **Automated:** `.github/workflows/digest.yml` runs daily at 01:00 UTC. Steps: install deps → run pipeline → commit digests + `published.json` → deploy to Cloudflare Pages.
- Requires GitHub secrets (see Owner's guide §3).
- `permissions: contents: write` is needed for the commit step.

## 9. Security

- `.env` is git-ignored; never commit it.
- Secrets live only in GitHub Actions secrets and your local `.env`.
- The site is fully static — no server, no database, no user data collected.
- Beehiiv/Resend handle subscriber data and unsubscribe compliance.

## 10. Testing / dry runs

There are no automated tests. To test safely:
- `python3 -m src.run` — skips if today's digest exists.
- `FORCE_RUN=1 python3 -m src.run` — forces a full run (will create a Beehiiv post).
- To test publishing without re-running the pipeline, load `public/digest.json` and call `publish.publish_all(...)`.
- To test the LLM fallback, unset `ANTHROPIC_API_KEY` and set `LLM_PROVIDER=anthropic`.

## 11. Known issues / future work

- Technology section is force-injected from TechCabal; may be thin if TechCabal is down.
- No RSS feed, search, dark mode, or custom domain yet (see `ROADMAP.md`).
- Beehiiv post status is `confirmed` (publishes immediately) — change to `draft` in `publish.py` to review first.
- The archive only includes digests committed to git; local runs don't persist unless committed.

## 12. Conventions

- Python 3.11+ (tested on 3.14). Use `python3`, not `python`.
- All paths are relative to the project root; `run.py` inserts the project root into `sys.path`.
- `load_dotenv()` is called in `run.py`; modules read env via `os.getenv`.
- Templates use Jinja2 with autoescape enabled.
- Commits follow conventional-ish messages; the bot commits as `github-actions[bot]`.
EOF