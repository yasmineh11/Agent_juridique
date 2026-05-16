"""
scraper.py — 9anoun.tn fetcher for the Agent Juridique Tunisien
================================================================

After direct inspection of the real sites:

  • 9anoun.tn        → plain server-rendered HTML, no JS needed
                       works perfectly with a simple httpx GET
  • iort.gov.tn      → 2000s WinDev app, all navigation via
                       javascript:{} links with session tokens
                       → CANNOT be scraped programmatically

Decision: use 9anoun.tn as the single authoritative source for BOTH:
  - Legal codes  : https://9anoun.tn/kb/codes/{slug}
  - JORT issues  : https://9anoun.tn/kb/jorts              (index)
                   https://9anoun.tn/kb/jorts/{jort-slug}  (one issue)

9anoun.tn already mirrors every JORT issue in clean HTML, so we lose
nothing by dropping iort.gov.tn.

URL patterns confirmed by live inspection:
  Codes index   : https://9anoun.tn/kb/codes
  One code      : https://9anoun.tn/kb/codes/code-travail-proposition-amendements-2025
  One article   : https://9anoun.tn/kb/codes/code-travail-.../code-travail-...-article-1
  JORT index    : https://9anoun.tn/kb/jorts
  One JORT      : https://9anoun.tn/kb/jorts/jort-2026-035-289f9

Install:
    pip install httpx[http2] beautifulsoup4
"""

import time
from typing import Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

# ── HTTP client config ────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar-TN,ar;q=0.9,fr;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BASE_9ANOUN     = "https://9anoun.tn"
BASE_9ANOUN_FR  = "https://9anoun.tn/fr"   # French version of same content
MAX_CONTENT_CHARS = 6000
MIN_PARA_LEN      = 40

# ── In-memory response cache ──────────────────────────────────────
_cache: dict[str, tuple[float, str]] = {}
CACHE_TTL = 3600  # 1 hour


def _cache_get(url: str) -> Optional[str]:
    if url in _cache:
        ts, content = _cache[url]
        if time.time() - ts < CACHE_TTL:
            print(f"  📦 Cache hit: {url[:70]}")
            return content
        del _cache[url]
    return None


def _cache_set(url: str, content: str) -> None:
    if content:
        _cache[url] = (time.time(), content)


# ── HTML extraction ───────────────────────────────────────────────

def _extract_text(html: str) -> str:
    """
    Extract clean Arabic/French legal text from 9anoun.tn HTML.
    The site structure uses <a> links in a .فهرس (index) div for article
    lists, and <p> / <div> tags for article body text.
    We prioritise article body content over navigation links.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove pure nav/chrome elements
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "noscript", "svg", "img"]):
        tag.decompose()

    paragraphs: list[str] = []

    # 1. Article body paragraphs (most specific)
    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) >= MIN_PARA_LEN:
            paragraphs.append(text)

    if paragraphs:
        return "\n\n".join(paragraphs)[:MAX_CONTENT_CHARS]

    # 2. Fallback: meaningful <a> link text (article index / JORT listing)
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        href = a["href"]
        if len(text) >= MIN_PARA_LEN and "9anoun.tn" in href or href.startswith("/kb"):
            links.append(f"{text}  →  {href}")

    if links:
        return "\n".join(links)[:MAX_CONTENT_CHARS]

    # 3. Last resort: raw visible text
    return soup.get_text(" ", strip=True)[:MAX_CONTENT_CHARS]


# ── Core fetch ────────────────────────────────────────────────────

def _fetch(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch a 9anoun.tn URL and return extracted text.
    Uses a persistent httpx client with HTTP/2.
    Returns None on any error.
    """
    cached = _cache_get(url)
    if cached is not None:
        return cached

    try:
        with httpx.Client(
            headers=HEADERS,
            follow_redirects=True,
            timeout=timeout,
            http2=True,
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()

        text = _extract_text(resp.text)
        _cache_set(url, text)
        return text or None

    except httpx.HTTPStatusError as e:
        print(f"  ✗ HTTP {e.response.status_code}: {url[:70]}")
        return None
    except Exception as e:
        print(f"  ✗ Fetch error ({url[:60]}): {e}")
        return None


# ── Code slug map ─────────────────────────────────────────────────
# Maps French/Arabic keywords → 9anoun.tn /kb/codes/{slug}
# Confirmed from live /kb/codes listing (May 2026).

_CODE_SLUGS: dict[str, str] = {
    # Code du Travail / مجلة الشغل
    "travail":        "code-travail-proposition-amendements-2025",
    "شغل":            "code-travail-proposition-amendements-2025",
    "licenciement":   "code-travail-proposition-amendements-2025",
    "préavis":        "code-travail-proposition-amendements-2025",
    "preavis":        "code-travail-proposition-amendements-2025",
    "salaire":        "code-travail-proposition-amendements-2025",
    "congé":          "code-travail-proposition-amendements-2025",
    "conge":          "code-travail-proposition-amendements-2025",
    "syndicat":       "code-travail-proposition-amendements-2025",
    "grève":          "code-travail-proposition-amendements-2025",
    "greve":          "code-travail-proposition-amendements-2025",
    "indemnité":      "code-travail-proposition-amendements-2025",
    "indemnite":      "code-travail-proposition-amendements-2025",
    "manaola":        "code-travail-proposition-amendements-2025",   # مناولة
    "مناولة":         "code-travail-proposition-amendements-2025",
    # Code des Obligations et Contrats / مجلة الالتزامات والعقود
    "obligations":    "code-obligations-contrats",
    "عقود":           "code-obligations-contrats",
    "التزامات":       "code-obligations-contrats",
    "contrat":        "code-obligations-contrats",
    "loyer":          "code-obligations-contrats",
    "bail":           "code-obligations-contrats",
    "responsabilité": "code-obligations-contrats",
    "responsabilite": "code-obligations-contrats",
    "dommages":       "code-obligations-contrats",
    "vente":          "code-obligations-contrats",
    # Code de Commerce / المجلة التجارية
    "commerce":       "code-commerce",
    "تجاري":          "code-commerce",
    "المجلة التجارية":"code-commerce",
    "société":        "code-commerce",
    "societe":        "code-commerce",
    "faillite":       "code-commerce",
    "chèque":         "code-commerce",
    "cheque":         "code-commerce",
    # Code Fiscal / مجلة الضريبة
    "impôt":          "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
    "impot":          "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
    "ضريبة":          "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
    "fiscal":         "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
    "taxe":           "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
    "tva":            "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
    # Code de Procédure Civile / مجلة المرافعات المدنية والتجارية
    "procédure":      "code-procedure-civile-commerciale",
    "procedure":      "code-procedure-civile-commerciale",
    "مرافعات":        "code-procedure-civile-commerciale",
    "délai":          "code-procedure-civile-commerciale",
    "delai":          "code-procedure-civile-commerciale",
    "recours":        "code-procedure-civile-commerciale",
    "tribunal":       "code-procedure-civile-commerciale",
    "jugement":       "code-procedure-civile-commerciale",
    "appel":          "code-procedure-civile-commerciale",
    "cassation":      "code-procedure-civile-commerciale",
    # Code des Douanes / مجلة الديوانة
    "douane":         "code-douanes",
    "ديوانة":         "code-douanes",
    "importation":    "code-douanes",
    "exportation":    "code-douanes",
    # Code des Collectivités Locales / مجلة الجماعات المحلية
    "municipalité":   "code-collectivites-locales",
    "municipalite":   "code-collectivites-locales",
    "commune":        "code-collectivites-locales",
    "جماعات محلية":   "code-collectivites-locales",
    # Code de Commerce Maritime / مجلة التجارة البحرية
    "maritime":       "code-commerce-maritime",
    "بحري":           "code-commerce-maritime",
    # Code des Droits Réels / مجلة الحقوق العينية
    "propriété":      "code-droits-reels",
    "propriete":      "code-droits-reels",
    "immobilier":     "code-droits-reels",
    "foncier":        "code-droits-reels",
    "hypothèque":     "code-droits-reels",
    "hypotheque":     "code-droits-reels",
    "حقوق عينية":     "code-droits-reels",
    # Code de Droit International Privé
    "international":  "code-droit-international-prive",
    "nationalité":    "code-droit-international-prive",
    "nationalite":    "code-droit-international-prive",
    # Code de la Comptabilité Publique / مجلة المحاسبة العمومية
    "comptabilité":   "code-comptabilite-publique",
    "comptabilite":   "code-comptabilite-publique",
    "محاسبة":         "code-comptabilite-publique",
    # Code des Changes (2024)
    "changes":        "projet-code-des-changes-2024",
    "devise":         "projet-code-des-changes-2024",
    "صرف":            "projet-code-des-changes-2024",
}


def _keyword_to_slug(keywords: str) -> Optional[str]:
    """Return the best matching code slug for a keyword string, or None."""
    kw_lower = keywords.lower()
    for key, slug in _CODE_SLUGS.items():
        if key.lower() in kw_lower:
            return slug
    return None


# ── Public API ────────────────────────────────────────────────────

def fetch_9anoun_code(keywords: str) -> tuple[str, str]:
    """
    Fetch the most relevant 9anoun.tn legal code page for the keywords.

    Strategy:
      1. Try to match a known code slug → direct URL fetch (most precise)
      2. Fall back to the /kb/codes listing (returns article index)

    Returns: (content, source_url)
    """
    slug = _keyword_to_slug(keywords)

    if slug:
        url = f"{BASE_9ANOUN}/kb/codes/{slug}"
        print(f"  🔍 9anoun code: {url}")
        content = _fetch(url)
        if content:
            return content, url

        # Try French version as fallback
        url_fr = f"{BASE_9ANOUN_FR}/kb/codes/{slug}"
        content = _fetch(url_fr)
        if content:
            return content, url_fr

    # No slug match → fetch the full codes listing
    url_list = f"{BASE_9ANOUN}/kb/codes"
    print(f"  🔍 9anoun codes index: {url_list}")
    content = _fetch(url_list)
    return (content or "", url_list)


def fetch_9anoun_jort(keywords: str) -> tuple[str, str]:
    """
    Fetch JORT content from 9anoun.tn/kb/jorts.

    Strategy:
      1. Fetch the JORT index to get recent issue slugs
      2. Try to find the most relevant issue by keyword match in titles
      3. If no match, return the full index listing (recent issues)

    Returns: (content, source_url)
    """
    index_url = f"{BASE_9ANOUN}/kb/jorts"
    print(f"  🔍 9anoun JORT index: {index_url}")

    index_html_raw: Optional[str] = None
    cached = _cache_get(index_url)
    if cached is not None:
        index_html_raw = cached
    else:
        try:
            with httpx.Client(headers=HEADERS, follow_redirects=True,
                              timeout=10, http2=True) as client:
                resp = client.get(index_url)
                resp.raise_for_status()
                index_html_raw = resp.text
                _cache_set(index_url, index_html_raw)
        except Exception as e:
            print(f"  ✗ JORT index fetch error: {e}")
            return "", index_url

    if not index_html_raw:
        return "", index_url

    # Parse issue links from index
    soup = BeautifulSoup(index_html_raw, "html.parser")
    issue_links: list[tuple[str, str]] = []   # (title, absolute_url)

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True)
        if "/kb/jorts/jort-" in href and len(text) > 10:
            abs_url = href if href.startswith("http") else BASE_9ANOUN + href
            issue_links.append((text, abs_url))

    if not issue_links:
        # Return whatever text the index contains
        content = _extract_text(index_html_raw)
        return content, index_url

    # Try to find the most keyword-relevant issue
    kw_lower = keywords.lower()
    best_url: Optional[str] = None
    for title, url in issue_links:
        if any(kw in title.lower() for kw in kw_lower.split()):
            best_url = url
            break

    # Default: fetch the most recent issue (first in list)
    target_url = best_url or issue_links[0][1]
    print(f"  🔍 9anoun JORT issue: {target_url}")
    content = _fetch(target_url)

    if content:
        return content, target_url

    # Fallback: return the index listing itself
    content = _extract_text(index_html_raw)
    return content, index_url
