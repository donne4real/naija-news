# Naija News Digest — Roadmap / Next Steps (saved 2026-11-18)

## Done
- [x] MVP pipeline: fetch RSS → dedup → rank → summarize (Claude Haiku + Gemini fallback) → render HTML/JSON
- [x] Cloudflare Pages deploy (manual via Wrangler) — live at https://naija-news.pages.dev
- [x] GitHub repo pushed: https://github.com/donne4real/naija-news

## Tomorrow
1. **Custom domain** — point a domain at the Pages project (Cloudflare dashboard → Pages → naija-news → Custom domains).
2. **Email delivery** — wire Resend (or Beehiiv) in `src/publish.py` using `RESEND_API_KEY` / `RESEND_TO`; test one send.
3. **Categories** — tag stories (politics, business, sports, etc.) and render grouped sections; possibly filter top 5 per category.
4. **Ranking tuning** — adjust dedup threshold and score weights in `src/dedup.py` (source count vs recency); add manual overrides.
5. **Archive / save each day** — ensure `public/digests/YYYY-MM-DD.html` accumulates; add an archive index page listing past digests.
6. **GitHub Actions secrets** — add the 7 secrets so the nightly cron auto-rebuilds.

## Secrets needed
LLM_PROVIDER, ANTHROPIC_API_KEY, LLM_FALLBACK_PROVIDER, GEMINI_API_KEY,
CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, PAGES_PROJECT_NAME
(+ optional RESEND_API_KEY/RESEND_FROM/RESEND_TO)
