#!/usr/bin/env python3
"""
SSF Portfolio Job Board - ATS Aggregator
Fetches open jobs from portfolio companies' public ATS feeds
(Greenhouse, Lever, Ashby) and writes a unified jobs.json.
"""

import json
import time
import requests
from datetime import datetime, timezone

COMPANIES_FILE = "companies.json"
OUTPUT_FILE = "jobs.json"
REQUEST_TIMEOUT = 10
SLEEP_BETWEEN = 0.3  # seconds, to be polite to APIs


# ── ATS endpoint templates ──────────────────────────────────────────────────

def _greenhouse_url(slug, content=False):
    base = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    return base + ("?content=true" if content else "")

def _lever_url(slug):
    return f"https://api.lever.co/v0/postings/{slug}?mode=json"

def _ashby_url(slug):
    return f"https://api.ashbyhq.com/posting-api/job-board/{slug}"


# ── Slug candidates from domain / name ─────────────────────────────────────

def slug_candidates(company: dict) -> list[str]:
    """Return a prioritised list of slug strings to try for a company."""
    domain = company.get("domain", "")
    name = company.get("name", "")
    seen, out = set(), []

    def add(s):
        s = s.lower().strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    if domain:
        add(domain.split(".")[0])           # "pika" from "pika.art"
        add(domain.replace(".", ""))        # "pikaart"
        without_tld = ".".join(domain.split(".")[:-1])
        add(without_tld)                    # "get.boltwise" → "getboltwise"
        add(without_tld.replace(".", ""))

    if name:
        add(name.replace(" ", "-"))         # "Cascading AI" → "cascading-ai"
        add(name.replace(" ", "").replace(".", ""))
        # first word only
        add(name.split()[0])

    return out


# ── ATS detection ───────────────────────────────────────────────────────────

def _get(url: str):
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"Accept": "application/json"})
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def detect_ats(company: dict) -> tuple[str | None, str | None]:
    """
    Try every slug candidate against Greenhouse → Lever → Ashby.
    Returns (ats_name, slug) or (None, None).
    """
    # If manually specified, use that directly.
    if company.get("ats") and company.get("slug"):
        return company["ats"], company["slug"]

    for slug in slug_candidates(company):
        # Greenhouse
        data = _get(_greenhouse_url(slug))
        if data and "jobs" in data:
            return "greenhouse", slug
        time.sleep(0.1)

        # Lever
        data = _get(_lever_url(slug))
        if isinstance(data, list):
            return "lever", slug
        time.sleep(0.1)

        # Ashby
        data = _get(_ashby_url(slug))
        if data and "jobPostings" in data:
            return "ashby", slug
        time.sleep(0.1)

    return None, None


# ── Job normalisation ────────────────────────────────────────────────────────

def _normalise_greenhouse(raw: dict, company: dict) -> dict:
    loc = raw.get("location") or {}
    depts = raw.get("departments") or [{}]
    return {
        "id": f"gh-{raw.get('id')}",
        "title": raw.get("title"),
        "company": company["name"],
        "company_domain": company.get("domain"),
        "location": loc.get("name") if isinstance(loc, dict) else str(loc),
        "department": depts[0].get("name") if depts else None,
        "apply_url": raw.get("absolute_url"),
        "posted_at": raw.get("updated_at"),
        "ats": "greenhouse",
    }

def _normalise_lever(raw: dict, company: dict) -> dict:
    cats = raw.get("categories") or {}
    ts = raw.get("createdAt")
    posted = (
        datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
        if ts else None
    )
    return {
        "id": f"lv-{raw.get('id')}",
        "title": raw.get("text"),
        "company": company["name"],
        "company_domain": company.get("domain"),
        "location": cats.get("location"),
        "department": cats.get("department"),
        "apply_url": raw.get("hostedUrl"),
        "posted_at": posted,
        "ats": "lever",
    }

def _normalise_ashby(raw: dict, company: dict) -> dict:
    loc = raw.get("locationName") or raw.get("location")
    if isinstance(loc, dict):
        loc = loc.get("name")
    return {
        "id": f"ash-{raw.get('id')}",
        "title": raw.get("title"),
        "company": company["name"],
        "company_domain": company.get("domain"),
        "location": loc,
        "department": raw.get("departmentName"),
        "apply_url": raw.get("jobUrl"),
        "posted_at": raw.get("publishedDate"),
        "ats": "ashby",
    }


# ── Fetchers ─────────────────────────────────────────────────────────────────

def fetch_jobs(ats: str, slug: str, company: dict) -> list[dict]:
    if ats == "greenhouse":
        data = _get(_greenhouse_url(slug, content=False)) or {}
        return [_normalise_greenhouse(j, company) for j in data.get("jobs", [])]

    if ats == "lever":
        data = _get(_lever_url(slug)) or []
        return [_normalise_lever(j, company) for j in (data if isinstance(data, list) else [])]

    if ats == "ashby":
        data = _get(_ashby_url(slug)) or {}
        return [_normalise_ashby(j, company) for j in data.get("jobPostings", [])]

    return []


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    with open(COMPANIES_FILE) as f:
        companies = json.load(f)

    all_jobs: list[dict] = []
    company_index: list[dict] = []

    for company in companies:
        print(f"  {company['name']} ({company.get('domain', '—')}) ", end="", flush=True)

        ats, slug = detect_ats(company)

        if ats:
            jobs = fetch_jobs(ats, slug, company)
            print(f"→ {ats}/{slug}  {len(jobs)} job(s)")
        else:
            jobs = []
            print("→ no ATS found")

        all_jobs.extend(jobs)
        company_index.append({
            "name": company["name"],
            "domain": company.get("domain"),
            "description": company.get("description", ""),
            "ats": ats,
            "slug": slug,
            "job_count": len(jobs),
        })

        time.sleep(SLEEP_BETWEEN)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_jobs": len(all_jobs),
        "total_companies": len(company_index),
        "companies": company_index,
        "jobs": all_jobs,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅  {len(all_jobs)} jobs across {len(company_index)} companies → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
