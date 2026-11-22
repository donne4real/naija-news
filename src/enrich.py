import re
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch_article_text(url, max_chars=4000):
    if not url:
        return ""
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": UA})
        r.raise_for_status()
    except Exception as e:
        print(f"[enrich] fetch failed {url}: {e}")
        return ""
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    node = soup.find("article") or soup.find("main")
    text = ""
    if node:
        text = node.get_text(" ", strip=True)
    if not text or len(text) < 200:
        for attr in ("description", "og:description", "twitter:description"):
            tag = soup.find("meta", attrs={"name": attr}) or soup.find("meta", attrs={"property": attr})
            if tag and tag.get("content"):
                text = tag["content"]
                break
    if not text or len(text) < 200:
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = " ".join(paras)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]
