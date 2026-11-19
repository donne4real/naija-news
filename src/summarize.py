import os
import json
import httpx

PROVIDERS = {
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "openrouter": ("https://openrouter.ai/api/v1", "openai/gpt-4o-mini"),
    "mistral": ("https://api.mistral.ai/v1", "mistral-small-latest"),
    "deepseek": ("https://api.deepseek.com/v1", "deepseek-chat"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-flash-latest"),
    "anthropic": ("https://api.anthropic.com/v1", "claude-haiku-4-5-20251001"),
    "together": ("https://api.together.xyz/v1", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
}

KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "together": "TOGETHER_API_KEY",
}

JSON_MODE_PROVIDERS = {"openai", "groq", "mistral", "deepseek", "gemini", "openrouter"}


def _resolve_provider(provider):
    provider = (provider or "openai").lower().strip()
    if provider not in PROVIDERS:
        provider = "openai"
    default_url, default_model = PROVIDERS[provider]
    # allow per-provider env overrides: LLM_BASE_URL only for primary; fallback uses defaults
    base_url = default_url
    model = os.getenv("LLM_MODEL", "").strip() if provider == os.getenv("LLM_PROVIDER", "openai").lower().strip() else default_model
    if not model:
        model = default_model
    # legacy openai model
    if provider == "openai" and not os.getenv("LLM_MODEL", "").strip():
        model = os.getenv("OPENAI_MODEL", "").strip() or default_model

    api_key = os.getenv("LLM_API_KEY", "").strip() if provider == os.getenv("LLM_PROVIDER", "openai").lower().strip() else ""
    if not api_key:
        api_key = os.getenv(KEY_ENV[provider], "").strip()
    if not api_key and provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
    return provider, base_url, model, api_key


def _resolve():
    primary = os.getenv("LLM_PROVIDER", "openai").lower().strip()
    p, url, model, key = _resolve_provider(primary)
    # base url override (primary only)
    override = os.getenv("LLM_BASE_URL", "").strip()
    if override:
        url = override
    if not model:
        model = PROVIDERS[p][1]
    return p, url, model, key


def _fallback_resolve():
    fb = os.getenv("LLM_FALLBACK_PROVIDER", "").lower().strip()
    if not fb:
        return None
    p, url, model, key = _resolve_provider(fb)
    if not key:
        return None
    fb_model = os.getenv("LLM_FALLBACK_MODEL", "").strip()
    if fb_model:
        model = fb_model
    return p, url, model, key


def _fallback(stories):
    out = []
    for s in stories:
        snippet = s.get("article_text") or " ".join(s.get("snippets", []))
        snippet = snippet[:400]
        out.append({
            "title": s["title"],
            "sources": s["sources"],
            "link": s["link"],
            "published": s["published"].isoformat(),
            "summary": snippet or "No summary available.",
            "why": "",
        })
    return out


def _call_llm(provider, base_url, model, api_key, stories):
    payload_stories = []
    for i, s in enumerate(stories, 1):
        text = s.get("article_text") or " ".join(s.get("snippets", []))
        payload_stories.append({
            "id": i,
            "title": s["title"],
            "sources": s["sources"],
            "text": text[:2500],
        })

    system = (
        "You are a Nigerian news editor. Given 5 news stories, write for each a concise "
        "2-3 sentence summary in clear English and a one-line 'why it matters'. "
        "Return ONLY valid JSON: an object with key 'items' containing an array of objects "
        "with keys: id, summary, why. No markdown."
    )
    user = json.dumps({"stories": payload_stories}, ensure_ascii=False)

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/naija-news"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
    }
    if provider in JSON_MODE_PROVIDERS:
        body["response_format"] = {"type": "json_object"}

    resp = httpx.post(url, headers=headers, json=body, timeout=90)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    # strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    data = json.loads(content)
    items = data.get("items", data if isinstance(data, list) else [])
    by_id = {it["id"]: it for it in items}

    out = []
    for i, s in enumerate(stories, 1):
        it = by_id.get(i, {})
        summary = it.get("summary") or " ".join(s.get("snippets", []))[:400]
        if not summary:
            raise ValueError("empty summary")
        out.append({
            "title": s["title"],
            "sources": s["sources"],
            "link": s["link"],
            "published": s["published"].isoformat(),
            "summary": summary,
            "why": it.get("why", ""),
        })
    if not out:
        raise ValueError("no items returned")
    return out


def summarize(stories):
    # try primary
    provider, base_url, model, api_key = _resolve()
    if not api_key:
        print(f"[summarize] no API key for primary '{provider}'; trying fallback")
    else:
        try:
            print(f"[summarize] using primary {provider} / {model}")
            return _call_llm(provider, base_url, model, api_key, stories)
        except Exception as e:
            print(f"[summarize] primary failed ({provider}): {e}")

    # try fallback provider
    fb = _fallback_resolve()
    if fb:
        f_provider, f_url, f_model, f_key = fb
        try:
            print(f"[summarize] using fallback {f_provider} / {f_model}")
            return _call_llm(f_provider, f_url, f_model, f_key, stories)
        except Exception as e:
            print(f"[summarize] fallback failed ({f_provider}): {e}")

    print("[summarize] all providers failed; using RSS snippets")
    return _fallback(stories)
