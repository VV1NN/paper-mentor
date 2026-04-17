#!/usr/bin/env python3
"""
search_papers.py — Search Semantic Scholar + DBLP + arXiv for a research topic,
filter by venue quality (top conferences + Q1 journals), rank by citations + recency.

Usage:
    python3 search_papers.py --topic "visual language action models" --years 5
    python3 search_papers.py --topic "indirect prompt injection LLM agents" --years 3 --top 15

Stderr: progress logs.  Stdout: JSON array of filtered & ranked papers.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pm_config import load_venue_db, survey_config, temp_file_path


# ── HTTP helper ─────────────────────────────────────────────────────────────

def fetch(url: str, timeout: int = 30, headers: Optional[dict] = None) -> str:
    h = {"User-Agent": "paper-mentor/1.0 (open source research tool)"}
    if headers:
        h.update(headers)
    try:
        req = Request(url, headers=h)
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        print(f"  [HTTP {e.code}] {url}", file=sys.stderr)
        return ""
    except (URLError, TimeoutError, Exception) as e:
        print(f"  [WARN] fetch failed {url[:80]}: {e}", file=sys.stderr)
        return ""


# ── Semantic Scholar ────────────────────────────────────────────────────────

SS_BASE = "https://api.semanticscholar.org/graph/v1"

def search_semantic_scholar(topic: str, years: int, limit: int, api_key: str = "") -> list[dict]:
    current_year = datetime.now().year
    year_filter = f"{current_year - years}-{current_year}"

    fields = ",".join([
        "title", "authors", "year", "venue", "citationCount", "referenceCount",
        "abstract", "externalIds", "publicationTypes", "journal", "publicationVenue",
    ])
    url = (
        f"{SS_BASE}/paper/search?"
        f"query={quote_plus(topic)}"
        f"&year={year_filter}"
        f"&limit={min(limit, 100)}"
        f"&fields={fields}"
    )

    headers = {"x-api-key": api_key} if api_key else {}
    print(f"  [Semantic Scholar] {topic} ({year_filter})...", file=sys.stderr)

    raw = fetch(url, timeout=45, headers=headers)
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [WARN] bad JSON from Semantic Scholar", file=sys.stderr)
        return []

    papers = []
    for item in data.get("data", []) or []:
        authors_raw = item.get("authors") or []
        authors = ", ".join(a.get("name", "") for a in authors_raw if a.get("name"))

        ext_ids = item.get("externalIds") or {}
        arxiv_id = ext_ids.get("ArXiv", "")
        doi = ext_ids.get("DOI", "")

        venue_raw = item.get("venue") or ""
        pub_venue = item.get("publicationVenue") or {}
        if isinstance(pub_venue, dict) and pub_venue.get("name"):
            venue_raw = pub_venue["name"]

        journal = item.get("journal") or {}
        journal_name = ""
        if isinstance(journal, dict):
            journal_name = journal.get("name", "") or ""

        papers.append({
            "title": (item.get("title") or "").strip(),
            "authors": authors,
            "year": item.get("year") or 0,
            "venue": venue_raw,
            "journal": journal_name,
            "citation_count": item.get("citationCount") or 0,
            "abstract": item.get("abstract") or "",
            "arxiv_id": arxiv_id,
            "doi": doi,
            "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else (
                f"https://doi.org/{doi}" if doi else ""
            ),
            "publication_types": item.get("publicationTypes") or [],
            "source": "semantic_scholar",
        })

    print(f"    → {len(papers)} papers", file=sys.stderr)
    return papers


# ── DBLP ─────────────────────────────────────────────────────────────────────

def search_dblp(topic: str, limit: int = 50) -> list[dict]:
    url = f"https://dblp.org/search/publ/api?q={quote_plus(topic)}&format=json&h={limit}"
    print(f"  [DBLP] {topic}...", file=sys.stderr)
    raw = fetch(url, timeout=30)
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    hits_obj = (data.get("result") or {}).get("hits") or {}
    hits = hits_obj.get("hit") or []

    papers = []
    for h in hits:
        info = h.get("info") or {}

        authors_obj = info.get("authors") or {}
        author_list = authors_obj.get("author") or []
        if isinstance(author_list, dict):
            author_list = [author_list]
        names = []
        for a in author_list:
            if isinstance(a, dict):
                names.append(a.get("text", ""))
            elif isinstance(a, str):
                names.append(a)
        authors = ", ".join(n for n in names if n)

        venue_raw = info.get("venue") or ""
        if isinstance(venue_raw, list):
            venue_raw = ", ".join(str(v) for v in venue_raw)

        year_val = info.get("year") or "0"
        try:
            year = int(year_val)
        except (ValueError, TypeError):
            year = 0

        doi = info.get("doi") or ""

        papers.append({
            "title": (info.get("title") or "").strip().rstrip("."),
            "authors": authors,
            "year": year,
            "venue": venue_raw,
            "journal": "",
            "citation_count": 0,
            "abstract": "",
            "arxiv_id": "",
            "doi": doi,
            "url": info.get("url") or (f"https://doi.org/{doi}" if doi else ""),
            "publication_types": [info.get("type") or ""],
            "source": "dblp",
        })

    print(f"    → {len(papers)} papers", file=sys.stderr)
    return papers


# ── arXiv ────────────────────────────────────────────────────────────────────

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

def search_arxiv(topic: str, limit: int = 50) -> list[dict]:
    url = (
        f"https://export.arxiv.org/api/query?"
        f"search_query=all:{quote_plus(topic)}"
        f"&sortBy=relevance&sortOrder=descending"
        f"&max_results={limit}"
    )
    print(f"  [arXiv] {topic}...", file=sys.stderr)
    raw = fetch(url, timeout=45)
    if not raw:
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []

    papers = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title_el = entry.find("atom:title", ATOM_NS)
        summary_el = entry.find("atom:summary", ATOM_NS)
        published_el = entry.find("atom:published", ATOM_NS)
        id_el = entry.find("atom:id", ATOM_NS)

        if title_el is None or summary_el is None:
            continue

        title = " ".join((title_el.text or "").split())
        abstract = " ".join((summary_el.text or "").split())
        url_val = (id_el.text or "").strip() if id_el is not None else ""
        date = (published_el.text or "")[:10] if published_el is not None else ""
        year = int(date[:4]) if date[:4].isdigit() else 0
        arxiv_id = url_val.split("/abs/")[-1] if "/abs/" in url_val else ""
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)

        authors_list = []
        for a in entry.findall("atom:author", ATOM_NS):
            name_el = a.find("atom:name", ATOM_NS)
            if name_el is not None and name_el.text:
                authors_list.append(name_el.text.strip())
        authors = ", ".join(authors_list)

        papers.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": "arXiv",
            "journal": "",
            "citation_count": 0,
            "abstract": abstract,
            "arxiv_id": arxiv_id,
            "doi": "",
            "url": url_val,
            "publication_types": ["Preprint"],
            "source": "arxiv",
        })

    print(f"    → {len(papers)} papers", file=sys.stderr)
    return papers


# ── Dedup ────────────────────────────────────────────────────────────────────

def normalize_title(t: str) -> str:
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def dedup_papers(all_papers: list[dict]) -> list[dict]:
    """Merge by DOI → arXiv ID → normalized title. Prefer records with more metadata."""
    by_key: dict[str, dict] = {}

    def metadata_score(p: dict) -> int:
        s = 0
        if p.get("citation_count", 0) > 0: s += 3
        if p.get("abstract"): s += 2
        if p.get("venue"): s += 2
        if p.get("doi"): s += 1
        if p.get("arxiv_id"): s += 1
        return s

    def merge(existing: dict, new: dict) -> dict:
        merged = dict(existing)
        for k, v in new.items():
            if k == "source":
                old = merged.get("source", "")
                if old and v and v not in old:
                    merged["source"] = f"{old}+{v}"
                continue
            if not merged.get(k) and v:
                merged[k] = v
            elif k == "citation_count" and (new.get(k) or 0) > (merged.get(k) or 0):
                merged[k] = new[k]
            elif k == "abstract" and len(v or "") > len(merged.get(k) or ""):
                merged[k] = v
        return merged

    for p in all_papers:
        keys = []
        if p.get("doi"):
            keys.append(f"doi:{p['doi'].lower()}")
        if p.get("arxiv_id"):
            keys.append(f"arxiv:{p['arxiv_id']}")
        title_norm = normalize_title(p.get("title", ""))
        if title_norm:
            keys.append(f"title:{title_norm}")

        if not keys:
            continue

        matched = None
        for k in keys:
            if k in by_key:
                matched = by_key[k]
                break

        if matched is None:
            for k in keys:
                by_key[k] = p
        else:
            merged = merge(matched, p)
            for k in keys:
                by_key[k] = merged
            for k, existing in list(by_key.items()):
                if existing is matched:
                    by_key[k] = merged

    seen_ids = set()
    unique = []
    for p in by_key.values():
        pid = id(p)
        if pid in seen_ids:
            continue
        seen_ids.add(pid)
        unique.append(p)

    return unique


# ── Venue matching + ranking ────────────────────────────────────────────────

def _normalize_venue_str(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\bproceedings of( the)?\b", "", s)
    s = re.sub(r"\b(19|20)\d{2}\b", "", s)
    s = re.sub(r"[^a-z0-9&]+", " ", s)
    return " ".join(s.split())


def classify_venue(venue: str, journal: str, db: dict) -> tuple[str, str]:
    """Return (tier, canonical_name). tier ∈ {tier1, tier2, q1_journal, preprint, unranked}."""
    candidates = [x for x in [venue, journal] if x]
    if not candidates:
        return ("unranked", "")

    aliases = db.get("venue_aliases", {})

    norm_candidates = [_normalize_venue_str(c) for c in candidates]

    for canonical, alias_list in aliases.items():
        canonical_norm = _normalize_venue_str(canonical)
        for alias in alias_list:
            alias_norm = _normalize_venue_str(alias)
            for cand in norm_candidates:
                if not cand:
                    continue
                if cand == alias_norm or cand == canonical_norm:
                    return _tier_of(canonical, db), canonical
                if (alias_norm and alias_norm in cand) or (len(cand) >= 4 and cand in alias_norm):
                    return _tier_of(canonical, db), canonical

    for tier_name in ("tier1", "tier2"):
        groups = db.get("conferences", {}).get(tier_name, {})
        for _, venue_list in groups.items():
            for v in venue_list:
                v_norm = _normalize_venue_str(v)
                for cand in norm_candidates:
                    if cand == v_norm or (v_norm and v_norm in cand):
                        return tier_name, v

    for j in db.get("journals", {}).get("q1", []):
        j_norm = _normalize_venue_str(j)
        for cand in norm_candidates:
            if cand == j_norm or (j_norm and j_norm in cand):
                return "q1_journal", j

    low = " ".join(norm_candidates)
    if "arxiv" in low or "preprint" in low or "corr" in low:
        return "preprint", "arXiv"

    return "unranked", candidates[0]


def _tier_of(canonical: str, db: dict) -> str:
    for tier_name in ("tier1", "tier2"):
        for _, venue_list in db.get("conferences", {}).get(tier_name, {}).items():
            if canonical in venue_list:
                return tier_name
    if canonical in db.get("journals", {}).get("q1", []):
        return "q1_journal"
    return "unranked"


TIER_SCORES = {"tier1": 3, "q1_journal": 3, "tier2": 2, "preprint": 0, "unranked": 0}


def compute_score(p: dict) -> float:
    tier = p.get("venue_tier", "unranked")
    tier_score = TIER_SCORES.get(tier, 0)

    citations = p.get("citation_count", 0) or 0
    citation_score = math.log2(citations + 1) * 2

    year = p.get("year", 0) or 0
    current_year = datetime.now().year
    age = current_year - year if year > 0 else 99
    if age <= 1: recency = 2
    elif age <= 2: recency = 1
    elif age <= 4: recency = 0.5
    else: recency = 0

    return tier_score * 3 + citation_score + recency


def filter_and_rank(papers: list[dict], cfg: dict, db: dict) -> list[dict]:
    min_citations = cfg.get("min_citation_count", 5)
    max_final = cfg.get("max_papers_final", 15)
    include_preprints = cfg.get("include_preprints", False)

    enriched = []
    unmatched_venues = set()

    for p in papers:
        tier, canonical = classify_venue(p.get("venue", ""), p.get("journal", ""), db)
        p["venue_tier"] = tier
        p["venue_canonical"] = canonical
        p["score"] = compute_score(p)
        enriched.append(p)

        if tier == "unranked" and p.get("venue"):
            unmatched_venues.add(p["venue"])

    if unmatched_venues:
        print(f"  [INFO] {len(unmatched_venues)} unmatched venues (add to venue_db.json if top-tier):", file=sys.stderr)
        for v in sorted(unmatched_venues)[:10]:
            print(f"    - {v}", file=sys.stderr)

    filtered = []
    for p in enriched:
        tier = p["venue_tier"]
        citations = p.get("citation_count", 0) or 0

        if tier in ("tier1", "tier2", "q1_journal"):
            filtered.append(p)
            continue

        if citations >= 100:
            filtered.append(p)
            continue

        if include_preprints and tier == "preprint" and citations >= min_citations:
            filtered.append(p)
            continue

    filtered.sort(key=lambda x: x["score"], reverse=True)
    return filtered[:max_final]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Search + quality-filter papers by topic")
    parser.add_argument("--topic", required=True, help="Research topic / question")
    parser.add_argument("--years", type=int, default=None, help="How many years back to search")
    parser.add_argument("--top", type=int, default=None, help="Max final papers (default from config)")
    parser.add_argument("--include-preprints", action="store_true", help="Allow high-cited arXiv preprints")
    parser.add_argument("--output", default=None, help="Output JSON path (default: /tmp/pm_survey_candidates.json)")
    args = parser.parse_args()

    cfg = dict(survey_config())
    if args.top is not None: cfg["max_papers_final"] = args.top
    if args.include_preprints: cfg["include_preprints"] = True
    years = args.years if args.years is not None else cfg.get("year_range_default", 5)
    search_limit = cfg.get("max_papers_per_search", 100)

    db = load_venue_db()
    api_key = cfg.get("semantic_scholar_api_key", "") or ""

    print(f"[search_papers] topic=\"{args.topic}\" years={years} top={cfg['max_papers_final']}", file=sys.stderr)

    ss = search_semantic_scholar(args.topic, years, search_limit, api_key)
    time.sleep(0.5)
    dblp = search_dblp(args.topic, limit=50)
    time.sleep(0.5)
    arxiv = search_arxiv(args.topic, limit=50)

    all_papers = ss + dblp + arxiv
    print(f"  Total before dedup: {len(all_papers)}", file=sys.stderr)

    unique = dedup_papers(all_papers)
    print(f"  After dedup: {len(unique)}", file=sys.stderr)

    current_year = datetime.now().year
    filtered_by_year = [p for p in unique if (p.get("year") or 0) >= current_year - years or (p.get("year") or 0) == 0]
    print(f"  After year filter: {len(filtered_by_year)}", file=sys.stderr)

    ranked = filter_and_rank(filtered_by_year, cfg, db)
    print(f"  Final: {len(ranked)} papers", file=sys.stderr)

    output_path = Path(args.output) if args.output else temp_file_path("pm_survey_candidates.json")
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(ranked, f, ensure_ascii=False, indent=2)
    print(f"  → {output_path}", file=sys.stderr)

    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    json.dump(ranked, sys.stdout, ensure_ascii=False, indent=2)
    print(file=sys.stdout)


if __name__ == "__main__":
    main()
