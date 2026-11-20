# Naija News Digest — Owner's guide

Everything you need to run, look after and change Naija News Digest. Day to day, **you don't need to do anything** — it updates and republishes itself every night.

## 1. The moving parts

| Part | What it does | Where you manage it |
|---|---|---|
| **GitHub repository** `donne4real/naija-news` (public) | Holds the code, the daily digests (`public/digests/`), `published.json`, and runs the scheduled job | github.com → the repo → **Actions**, **Settings** |
| **News sources** (RSS feeds) | ~13 Nigerian news sites supply the headlines | `src/sites.py` in the repo |
| **Anthropic Claude Haiku** | Writes the summaries and categories | console.anthropic.com |
| **Google Gemini Flash** | Automatic fallback if Claude fails | aistudio.google.com |
| **Cloudflare Pages** project `naija-news` | Hosts the website at https://naija-news.pages.dev | dash.cloudflare.com → Workers & Pages |
| **Beehiiv** publication `naija-news-digest` | Email newsletter + subscriber management + monetization | app.beehiiv.com |
| **Resend** (optional) | Fallback email sender | resend.com |
| **Exchange-rate API** (open.er-api.com) | USD/GBP/EUR → NGN rates, free, no key | — |
| **Your PC** `Vibe Coding\Reflection\naija-news` | Working copy of the code, plus `.env` with your keys | — |

## 2. The schedule (all automatic)

| When (UTC) | Virginia time | Job | What it does |
|---|---|---|---|
| 01:00 daily | ~20:00/21:00 (8/9 pm) | Daily digest | Fetches feeds, dedups, ranks, summarizes, renders, posts to Beehiiv, commits the digest, deploys to Cloudflare Pages |

GitHub sometimes starts scheduled jobs 5–20 minutes late; that's normal. The digest filename is the UTC date (`YYYY-MM-DD`).

**If today's digest already exists** (e.g. you ran it manually), the job skips automatically to avoid overwriting and duplicate stories. To force a re-run, set the `FORCE_RUN=1` environment variable (or run locally with `FORCE_RUN=1 python3 -m src.run`).

## 3. Accounts, keys and secrets

| Secret | From | Stored in |
|---|---|---|
| `LLM_PROVIDER` | — (set to `anthropic`) | `.env` + GitHub secret |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | `.env` + GitHub secret |
| `LLM_FALLBACK_PROVIDER` | — (set to `gemini`) | `.env` + GitHub secret |
| `GEMINI_API_KEY` | aistudio.google.com → API keys | `.env` + GitHub secret |
| `CLOUDFLARE_API_TOKEN` | Cloudflare → My Profile → API Tokens (Pages: Edit) | `.env` + GitHub secret |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard, right sidebar | `.env` + GitHub secret |
| `PAGES_PROJECT_NAME` | — (set to `naija-news`) | `.env` + GitHub secret |
| `BEEHIIV_API_KEY` | Beehiiv → Settings → Integrations → API | `.env` + GitHub secret |
| `BEEHIIV_PUBLICATION_ID` | Beehiiv → Settings → General | `.env` + GitHub secret |
| `BEEHIIV_SUBSCRIBE_URL` | your publication's subscribe page | `.env` + GitHub secret |
| `RESEND_API_KEY` / `RESEND_FROM` / `RESEND_TO` | resend.com (optional fallback) | `.env` + GitHub secret |

Tuning vars (optional, defaults shown): `DEDUP_THRESHOLD=0.45`, `RANK_SOURCE_WEIGHT=2`, `RANK_RECENCY_HOURS=48`, `TOP_N=24`, `DIGEST_SIZE=15`, `MAX_PER_CATEGORY=3`.

- **`.env` is git-ignored** and must never be committed or shared. Keep a copy in a password manager.
- GitHub secrets live at **repo → Settings → Secrets and variables → Actions**. GitHub never shows a secret's value again; you can only replace it.

**Replacing a key:** create the new key at the provider, update `.env`, then replace it on the GitHub secrets page (or ask Claude to run `gh secret set`). Revoke the old key at the provider.

## 4. Checking that it's working

- **The site header** shows the digest date. After ~01:00 UTC it should be today's date.
- **GitHub → Actions → Daily Naija News Digest** lists every run with a green ✓ or red ✗. Open a run to see lines such as:
  - `using primary anthropic / claude-haiku-4-5-20251001` — LLM used
  - `balanced to 15 items: {...}` — final category counts
  - `recorded N new links in published.json` — dedup tracking
  - `beehiiv post created` — newsletter sent
- **`public/digests/`** in the repo grows by one file per day.
- **`published.json`** grows as stories are featured (prevents repeats).
- **Beehiiv dashboard** shows the new post after each run.

## 5. When something goes wrong

GitHub emails you whenever a run **fails**. Most failures are one-offs and the next run fixes them.

| Symptom | Likely cause | What to do |
|---|---|---|
| Run fails at **fetching feeds** with timeouts | A news site is slow/down | Nothing — failed sources are skipped; the digest still builds from the rest |
| `no API key for primary 'anthropic'` | Secret missing or misnamed | Check GitHub secrets spelling: `ANTHROPIC_API_KEY` |
| `primary failed (anthropic): 404` | Model name outdated | Update `LLM_MODEL` (default `claude-haiku-4-5-20251001`) |
| `beehiiv failed: 422` | Payload shape changed | Check Beehiiv API docs; `body_content` field is required |
| Run fails at **Deploy to Cloudflare Pages** | Token expired or project missing | Replace `CLOUDFLARE_API_TOKEN`; ensure project `naija-news` exists |
| Run fails at **Commit daily digest** (push rejected) | Someone pushed to `main` during the run | Nothing — the next run redoes it |
| Digest shows stale stories / no new post | Job skipped because today's digest already exists | Run with `FORCE_RUN=1` (locally or via Actions env) |
| Everyone sees old digest | Deploy didn't run | Actions → Daily Naija News Digest → Run workflow |
| `digest for YYYY-MM-DD already exists; skipping` | Expected after a manual run | Set `FORCE_RUN=1` to override |

**Republish without fetching new data:** repo → **Actions** → **Daily Naija News Digest** → **Run workflow** (on a day already done it skips; add `FORCE_RUN=1` env to force).

**Pause everything:** Actions → Daily Naija News Digest → **⋯ → Disable workflow**. Re-enable the same way.

**Manual deploy from your PC:**
```bash
cd "Vibe Coding/Reflection/naija-news"
python3 -m src.run   # or FORCE_RUN=1 python3 -m src.run
CLOUDFLARE_API_TOKEN=... CLOUDFLARE_ACCOUNT_ID=... npx wrangler pages deploy public --project-name=naija-news --branch=main
```

## 6. Costs and limits

| Service | Plan | Limit that matters | Current use |
|---|---|---|---|
| Anthropic Claude Haiku | Pay-as-you-go | ~$0.25/M input tokens | ~15 stories/day → a few cents/month |
| Google Gemini Flash | Free tier | 15 RPM, 1M tokens/day | Fallback only |
| Beehiiv | Free up to 2,500 subs | Subscriber cap | Newsletter delivery + monetization |
| Resend | Free 3,000 emails/mo | Email count | Fallback sender only |
| GitHub | Free, public repo | 2,000 Actions min/month | ~3 min/run → ~90 min/month |
| Cloudflare Pages | Free | 500 builds/month | ~30/month |
| Exchange-rate API | Free | 1,500 req/month | 1/day |

**Total: under $1/month** at current scale.

## 7. Known limitations

- **End-of-day only**, once per day — not live news.
- **AI summaries** can occasionally mis-categorize or oversimplify; always follow the "Read original" link.
- **Dedup is title-based** — a story re-published under a new headline may slip through.
- **Technology section** is force-injected from TechCabal; if TechCabal is down, the section may be thin.
- **Exchange rates** are indicative reference rates, not bank quotes.
- **Beehiiv post status** is set to `confirmed` (publishes immediately). Change to `draft` in `src/publish.py` if you want to review before sending.
- **No unsubscribe handling on the site** — handled by Beehiiv/Resend emails.

## 8. Maintenance to-do

- **Add secrets to GitHub** (if not done): `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `LLM_FALLBACK_PROVIDER`, `GEMINI_API_KEY`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `PAGES_PROJECT_NAME`, `BEEHIIV_API_KEY`, `BEEHIIV_PUBLICATION_ID`, `BEEHIIV_SUBSCRIBE_URL` (+ optional Resend + tuning vars).
- **Custom domain:** Cloudflare dashboard → Pages → naija-news → Custom domains.
- **RSS feed** for the digest — implemented (`/feed.xml`, one item per daily roundup).
- **Search** across archived digests — not yet implemented.
- **Dark mode** toggle — not yet implemented.
- Once a year, check dependency updates: `pip list --outdated`, update `requirements.txt`, test, push.

## 9. Making changes

The simplest way is to ask Claude (in this project folder) for the change. For hands-on work, see the [Developer guide](developer-guide.md). Useful commands from `Vibe Coding\Reflection\naija-news`:

| Command | Does |
|---|---|
| `pip install -r requirements.txt` | Install dependencies |
| `python3 -m src.run` | Run the pipeline (skips if today's digest exists) |
| `FORCE_RUN=1 python3 -m src.run` | Force a re-run |
| `CLOUDFLARE_API_TOKEN=... npx wrangler pages deploy public --project-name=naija-news --branch=main` | Deploy manually |
| `git pull` | Bring down the bot's daily commits before editing |

Always `git pull` before editing — the bot commits to `main` every day.
EOF