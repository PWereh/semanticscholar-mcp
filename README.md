# Semantic Scholar MCP Server — COSTUDY Patch v2.0

A patched fork of [alperenkocyigit/semantic-scholar-graph-api](https://github.com/alperenkocyigit/semantic-scholar-graph-api) with targeted fixes for the **ARES-10-COSTUDY** academic pipeline.

## What Was Patched

| Fix | File | Impact |
|---|---|---|
| API key header injection via `S2_API_KEY` env var | `search.py` | Authenticated tier access; priority rate-limit queue |
| Expanded field sets — adds `externalIds` (DOI), `openAccessPdf`, `influentialCitationCount` | `search.py` | ANTIFRAGILE_TRACEABILITY chain integrity |
| `influential_only` param on citations/references | `search.py` | Phase 4 citation chaining per scholar-research skill spec |
| Unified `_fmt_paper()` normalizer — `doi` and `openAccessPdfUrl` as top-level fields | `search.py` | Eliminates post-processing in AIA |
| `/recommendations/v1/papers/forpaper/{id}` (current endpoint) | `search.py` | Fixes deprecated multi-paper recommendations URL |
| `snippet/search` endpoint with DOI extraction | `search.py` | Phase 3 deep retrieval without full PDF fetch |
| `S2_API_KEY` env slot in smithery.yaml | `smithery.yaml` | One-field config on Smithery deploy |
| PORT 8000 consistency; uvicorn CMD | `Dockerfile` | Matches Railway/Render/Smithery defaults |
| `render.yaml` added | — | One-click Render deploy |

## Quick Deploy

### Option 1 — Railway (recommended, free tier)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

1. Fork this repo
2. Connect to Railway → New Project → Deploy from GitHub
3. Add env var: `S2_API_KEY = <your key>`
4. Railway assigns a public URL (e.g. `https://semantic-scholar-mcp.up.railway.app`)

### Option 2 — Render
1. Fork this repo
2. Render → New Web Service → connect repo
3. Add env var: `S2_API_KEY = <your key>` in the Render dashboard
4. Render assigns a public URL

### Option 3 — Smithery (zero infrastructure)
1. Fork this repo and push to GitHub
2. Connect at [smithery.ai/new](https://smithery.ai/new)
3. Set `S2_API_KEY` in Smithery environment variables
4. Smithery hosts the server and provides an MCP URL

## Add to Claude.ai

Once deployed, add as a custom MCP connector:

1. `Claude.ai → Settings → Connectors → Add MCP Server`
2. URL: `https://<your-deployed-url>/mcp`  *(or the Smithery URL)*
3. Name: `semantic-scholar`

Claude will then have access to all 12 tools via the MCP gateway — bypassing the compute egress proxy that blocks `api.semanticscholar.org` from bash.

## Get an API Key

Free keys at [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api).  
Without a key the server works on S2's shared public pool (~1 req/s). With a key, requests are prioritized.

## Tools

| Tool | Endpoint | COSTUDY Phase |
|---|---|---|
| `search_semantic_scholar_papers` | `paper/search` | Phase 1 discovery |
| `get_semantic_scholar_papers_batch` | `paper/batch POST` | Phase 2 metadata harvest |
| `get_semantic_scholar_paper_details` | `paper/{id}` | Phase 3 deep retrieval |
| `get_semantic_scholar_citations_and_references` | `paper/{id}/citations+references` | Phase 4 chaining |
| `get_semantic_scholar_paper_recommendations` | `recommendations/v1/papers/forpaper/{id}` | Phase 1 lateral discovery |
| `get_semantic_scholar_paper_recommendations_from_lists` | `recommendations/v1/papers POST` | Phase 1 lateral discovery |
| `search_semantic_scholar_snippets` | `snippet/search` | Phase 3 (no PDF needed) |
| `get_semantic_scholar_paper_match` | `paper/search/match` | Citation validation |
| `get_semantic_scholar_paper_autocomplete` | `paper/autocomplete` | Query assist |
| `search_semantic_scholar_authors` | `author/search` | Authority verification |
| `get_semantic_scholar_author_details` | `author/{id}` | h-index / affiliation |
| `get_semantic_scholar_authors_batch` | `author/batch POST` | Bulk authority check |
