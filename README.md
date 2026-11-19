# Naija News Digest

Daily digest of top Nigerian news: fetches RSS from major outlets, dedups, ranks, summarizes top 5 with an LLM, publishes static HTML/JSON to Cloudflare Pages (and optional email via Resend).

## Run locally
```bash
cd naija-news
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill OPENAI_API_KEY for real summaries
python -m src.run
# open public/index.html
```

Without `LLM_API_KEY` (or provider key), falls back to RSS snippets.

## Switch LLM provider
Set `LLM_PROVIDER` to one of: openai, groq, openrouter, mistral, deepseek, gemini, anthropic, together.
Optionally override `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`. Provider-specific keys are also supported.

## Configure GitHub Actions secrets
OPENAI_API_KEY, OPENAI_MODEL, RESEND_* (optional), CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, PAGES_PROJECT_NAME.

## Edit sources
`src/sites.py`
