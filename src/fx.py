import httpx


def get_rates():
    """Return dict with NGN rates: usd, gbp, eur (NGN per 1 unit)."""
    out = {"usd": None, "gbp": None, "eur": None, "updated": None}
    try:
        r = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=20)
        r.raise_for_status()
        d = r.json()
        rates = d.get("rates", {})
        ngn = rates.get("NGN")
        if ngn:
            out["usd"] = ngn
            gbp = rates.get("GBP")
            eur = rates.get("EUR")
            if gbp:
                out["gbp"] = ngn / gbp
            if eur:
                out["eur"] = ngn / eur
            out["updated"] = d.get("time_last_update_utc")
    except Exception as e:
        print(f"[fx] failed: {e}")
    return out
