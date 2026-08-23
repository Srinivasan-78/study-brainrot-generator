#!/usr/bin/env python3
"""topic -> grounding text (Wikipedia REST API, no key needed)."""
import os
import sys
import time
import requests

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
MAX_RESEARCH_CHARS = 15000  # bound LLM input size

SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": "StudyBrainrotGenerator/1.0 (personal study project; https://github.com)"}
)


def wiki_get(params):
    """GET the API and surface an API-level error as a RequestException."""
    r = SESSION.get(WIKI_API_URL, params={**params, "format": "json"}, timeout=15)
    r.raise_for_status()
    try:
        payload = r.json()
    except ValueError as e:
        raise requests.RequestException(f"non-JSON response: {e}") from e
    if "error" in payload:
        info = payload["error"].get("info", payload["error"])
        raise requests.RequestException(f"Wikipedia API error: {info}")
    return payload


def wiki_search(topic, limit=3):
    # Over-fetch: disambiguation hits are dropped below and would otherwise
    # leave the script grounded on fewer articles than asked for.
    payload = wiki_get(
        {
            "action": "query",
            "list": "search",
            "srsearch": topic,
            "srlimit": limit + 2,
        }
    )
    results = payload.get("query", {}).get("search", [])
    titles = [
        item["title"]
        for item in results
        if item.get("title") and "(disambiguation)" not in item["title"]
    ]
    return titles[:limit]


def wiki_extract(title):
    # exlimit is fixed at 1: the API only allows batching extracts when they are
    # truncated to the intro, and the full article text is what grounds the script.
    payload = wiki_get(
        {
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "exsectionformat": "plain",
            "redirects": 1,
            "titles": title,
        }
    )
    pages = payload.get("query", {}).get("pages", {})
    if not pages:
        return ""
    page = next(iter(pages.values()))
    if "missing" in page:
        return ""
    return page.get("extract", "")


def pack(chunks, budget):
    """Trim sources to fit `budget` without letting the first one eat it all.

    Truncating the joined text would drop later sources entirely whenever the
    lead article is long, so each source gets an equal share and whatever the
    short ones don't use is handed back to the long ones.
    """
    if not chunks:
        return []
    remaining = budget
    packed = [None] * len(chunks)
    # Shortest first, so every source it fits releases its unused share.
    for rank, (i, text) in enumerate(sorted(enumerate(chunks), key=lambda t: len(t[1]))):
        share = remaining // (len(chunks) - rank)
        packed[i] = text[:share]
        remaining -= len(packed[i])
    return [t for t in packed if t]


def main():
    topic = os.environ.get("TOPIC") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not topic:
        print("ERROR: no topic provided (set TOPIC env var or pass as arg)", file=sys.stderr)
        sys.exit(1)

    print(f"[research] searching Wikipedia for: {topic}")
    try:
        titles = wiki_search(topic)
    except requests.RequestException as e:
        print(f"ERROR: Wikipedia search failed: {e}", file=sys.stderr)
        sys.exit(1)

    if not titles:
        print(f"ERROR: no Wikipedia results for '{topic}'", file=sys.stderr)
        sys.exit(1)

    chunks = []
    seen = set()
    for title in titles:
        try:
            text = wiki_extract(title)
        except requests.RequestException as e:
            print(f"[research] WARNING: failed to fetch '{title}': {e}", file=sys.stderr)
            continue
        if text and text not in seen:
            seen.add(text)
            chunks.append(f"== {title} ==\n{text}")
        time.sleep(0.3)

    if not chunks:
        print("ERROR: fetched zero usable pages", file=sys.stderr)
        sys.exit(1)

    sep = "\n\n"
    budget = MAX_RESEARCH_CHARS - len(sep) * max(len(chunks) - 1, 0)
    packed = pack(chunks, budget)
    combined = sep.join(packed)

    os.makedirs("build", exist_ok=True)
    with open("build/research.txt", "w", encoding="utf-8") as f:
        f.write(combined)

    # `packed`, not `chunks`: a source squeezed to nothing by the budget is dropped.
    print(f"[research] wrote build/research.txt ({len(combined)} chars, {len(packed)} sources)")


if __name__ == "__main__":
    main()
