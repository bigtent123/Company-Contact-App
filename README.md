# Company Contact Finder (Lean ZoomInfo/Apollo Alternative)

A lightweight, low-cost contact intelligence API focused on finding decision-maker contact paths at companies (hotel owners, executives, etc.).

## Why this approach
Instead of paying for an expensive all-in-one data broker, this project combines:

1. **OpenCorporates API** (company registry source, broad coverage, reliable)
2. **Hunter Domain Search API** (pattern-based professional emails, affordable tiers)
3. **Clearbit Name-to-Domain API** fallback (optional, low-friction company→domain mapping)

This keeps costs low while preserving useful signal quality.

## API recommendation (cost vs reliability)

### Primary company data API: OpenCorporates
- Reliable legal-entity data from government registries
- Excellent for company existence, officers/directors, jurisdiction, registration numbers
- Better long-term reliability than ad hoc scraped sources

### Contact path API: Hunter.io
- Good value for discovering likely emails by domain and role
- Transparent confidence scoring
- Lower cost than many full-stack sales-intel vendors

## Architecture

```
Client -> FastAPI Service
               ├─ CompanyResolver (OpenCorporates)
               ├─ DomainResolver (Hunter/optional Clearbit)
               └─ ContactFinder (Hunter + heuristic ranking)
```

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Environment variables

- `OPENCORPORATES_API_TOKEN` (recommended)
- `HUNTER_API_KEY` (recommended)
- `CLEARBIT_API_KEY` (optional)

## Endpoints

- `GET /health`
- `GET /search/company?name=Hilton&jurisdiction=us_nv`
- `GET /search/contacts?company_name=Hilton&title_hint=owner`

## Notes

- This is intentionally an MVP: reliable source stitching + scoring layer.
- For production, add caching (Redis), retries/circuit breakers, and background enrichment queues.
