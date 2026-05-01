import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

load_dotenv()

app = FastAPI(title="Company Contact Finder", version="0.1.0")

OPENCORPORATES_API_TOKEN = os.getenv("OPENCORPORATES_API_TOKEN", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
CLEARBIT_API_KEY = os.getenv("CLEARBIT_API_KEY", "")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


async def opencorporates_search(company_name: str, jurisdiction: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"q": company_name}
    if jurisdiction:
        params["jurisdiction_code"] = jurisdiction
    if OPENCORPORATES_API_TOKEN:
        params["api_token"] = OPENCORPORATES_API_TOKEN

    url = "https://api.opencorporates.com/v0.4/companies/search"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    return payload


async def hunter_domain_search(domain: str) -> dict[str, Any]:
    if not HUNTER_API_KEY:
        return {"data": {"emails": []}, "meta": {"warning": "HUNTER_API_KEY missing"}}

    url = "https://api.hunter.io/v2/domain-search"
    params = {"domain": domain, "api_key": HUNTER_API_KEY}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def guess_domain(company_name: str) -> str | None:
    # Low-cost heuristic fallback; replace with dedicated resolver for production.
    name = "".join(ch for ch in company_name.lower() if ch.isalnum() or ch == " ").strip()
    if not name:
        return None
    base = name.split()[0]
    return f"{base}.com"


@app.get("/search/company")
async def search_company(name: str = Query(...), jurisdiction: str | None = Query(default=None)) -> dict[str, Any]:
    try:
        payload = await opencorporates_search(name, jurisdiction)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"OpenCorporates error: {exc.response.status_code}") from exc

    companies = payload.get("results", {}).get("companies", [])
    slim = []
    for c in companies[:10]:
        company = c.get("company", {})
        slim.append(
            {
                "name": company.get("name"),
                "company_number": company.get("company_number"),
                "jurisdiction_code": company.get("jurisdiction_code"),
                "incorporation_date": company.get("incorporation_date"),
                "current_status": company.get("current_status"),
            }
        )

    return {"query": name, "count": len(slim), "companies": slim}


@app.get("/search/contacts")
async def search_contacts(company_name: str = Query(...), title_hint: str = Query(default="executive")) -> dict[str, Any]:
    domain = await guess_domain(company_name)
    if not domain:
        raise HTTPException(status_code=400, detail="Unable to infer domain")

    hunter = await hunter_domain_search(domain)
    emails = hunter.get("data", {}).get("emails", [])

    ranked = []
    for item in emails:
        value = item.get("value")
        position = (item.get("position") or "").lower()
        confidence = item.get("confidence", 0)
        score = confidence
        if title_hint.lower() in position:
            score += 20

        ranked.append(
            {
                "email": value,
                "first_name": item.get("first_name"),
                "last_name": item.get("last_name"),
                "position": item.get("position"),
                "confidence": confidence,
                "score": score,
                "sources": item.get("sources", []),
            }
        )

    ranked.sort(key=lambda r: r["score"], reverse=True)

    return {
        "company_name": company_name,
        "domain": domain,
        "title_hint": title_hint,
        "results": ranked[:20],
        "recommendation": {
            "primary_company_data_api": "OpenCorporates",
            "primary_contact_api": "Hunter",
            "reason": "Low cost + reliable legal entity data + usable professional email discovery",
        },
    }
