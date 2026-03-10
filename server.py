#!/usr/bin/env python3
"""
Semantic Scholar MCP Server — ARES-patched fork
Adds: x-api-key auth, expanded fields (DOI, openAccessPdf, influentialCitationCount),
      isInfluential filtering on citation/reference chains.
Transport: Streamable HTTP (Smithery / self-hosted) or stdio (local dev).
"""
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from mcp.server import FastMCP
from pydantic import BaseModel, Field

from search import (
    search_papers, get_paper_details, get_author_details,
    get_citations_and_references, get_paper_citations, get_paper_references,
    search_authors, search_paper_match, get_paper_autocomplete,
    get_papers_batch, get_authors_batch, search_snippets,
    get_paper_recommendations_from_lists, get_paper_recommendations,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastMCP("Semantic Scholar MCP Server — ARES Edition")


@app.tool()
async def search_semantic_scholar_papers(
    query: str,
    num_results: int = 25,
) -> List[Dict[str, Any]]:
    """
    Search Semantic Scholar. Returns papers with title, abstract, year, authors,
    DOI (externalIds.DOI), openAccessPdfUrl, citationCount, influentialCitationCount,
    publicationTypes, fieldsOfStudy, and tldr.
    Default num_results=25 (authenticated tier); max 100.
    """
    return await asyncio.to_thread(search_papers, query, num_results)


@app.tool()
async def get_semantic_scholar_paper_details(paper_id: str) -> Dict[str, Any]:
    """
    Full metadata for one paper. Accepts S2 paperId, DOI:10.x/y, or ARXIV:id.
    Returns all fields including referenceCount and openAccessPdfUrl.
    """
    return await asyncio.to_thread(get_paper_details, paper_id)


@app.tool()
async def get_semantic_scholar_author_details(author_id: str) -> Dict[str, Any]:
    """Author metadata: name, affiliations, hIndex, citationCount, paperCount."""
    return await asyncio.to_thread(get_author_details, author_id)


@app.tool()
async def get_semantic_scholar_citations(
    paper_id: str,
    limit: int = 50,
    influential_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Forward citation chain — papers that CITE this paper.
    Set influential_only=True to return only isInfluential=true papers (high-signal).
    Used in ARES Phase 4 forward chain (recent papers building on this work).
    """
    return await asyncio.to_thread(get_paper_citations, paper_id, limit, influential_only)


@app.tool()
async def get_semantic_scholar_references(
    paper_id: str,
    limit: int = 50,
    influential_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Backward reference chain — papers this paper CITES.
    Set influential_only=True for foundational/seminal sources only.
    Used in ARES Phase 4 backward chain.
    """
    return await asyncio.to_thread(get_paper_references, paper_id, limit, influential_only)


@app.tool()
async def get_semantic_scholar_citations_and_references(
    paper_id: str,
) -> Dict[str, Any]:
    """Combined citations + references in one call (default limits)."""
    return await asyncio.to_thread(get_citations_and_references, paper_id)


@app.tool()
async def search_semantic_scholar_authors(
    query: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Search authors by name. Returns authorId, hIndex, citationCount, affiliations."""
    return await asyncio.to_thread(search_authors, query, limit)


@app.tool()
async def get_semantic_scholar_paper_match(query: str) -> Dict[str, Any]:
    """
    Best-match paper by title. Returns matchScore + full paper schema.
    Use when you have a known title and want the canonical S2 record.
    """
    return await asyncio.to_thread(search_paper_match, query)


@app.tool()
async def get_semantic_scholar_paper_autocomplete(query: str) -> List[Dict[str, Any]]:
    """Autocomplete suggestions for partial paper title."""
    return await asyncio.to_thread(get_paper_autocomplete, query)


@app.tool()
async def get_semantic_scholar_papers_batch(
    paper_ids: List[str],
) -> List[Dict[str, Any]]:
    """
    Batch fetch up to 500 papers in one POST call.
    Accepts S2 paperIds, DOI:10.x/y, ARXIV:id.
    Use after Phase 1 discovery to pull full metadata on top candidates efficiently.
    """
    return await asyncio.to_thread(get_papers_batch, paper_ids)


@app.tool()
async def get_semantic_scholar_authors_batch(
    author_ids: List[str],
) -> List[Dict[str, Any]]:
    """Batch fetch up to 1000 authors."""
    return await asyncio.to_thread(get_authors_batch, author_ids)


@app.tool()
async def search_semantic_scholar_snippets(
    query: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    In-paper passage search. Returns text fragments with source paper context.
    Use in ARES Phase 3 to surface quotable passages and supporting statistics
    without needing a full PDF fetch. Each result includes score, snippet.text,
    snippet.section, and paper.title/authors.
    """
    return await asyncio.to_thread(search_snippets, query, limit)


@app.tool()
async def get_semantic_scholar_paper_recommendations(
    paper_id: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Recommendations for a single seed paper (/forpaper/ endpoint — current API).
    Use after Phase 1 to surface laterally-related papers missed by keyword search.
    Equivalent to ARES Phase 4 RECOMMENDATIONS sweep.
    """
    return await asyncio.to_thread(get_paper_recommendations, paper_id, limit)


@app.tool()
async def get_semantic_scholar_paper_recommendations_from_lists(
    positive_paper_ids: List[str],
    negative_paper_ids: List[str] = [],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Recommendations from explicit positive/negative paper lists.
    Use with top 2-3 Phase 1 results as positive seeds for broader lateral coverage.
    """
    return await asyncio.to_thread(
        get_paper_recommendations_from_lists,
        positive_paper_ids, negative_paper_ids or [], limit
    )


# ── HEALTH ROUTES ────────────────────────────────────────────────────────────
# FastMCP mounts MCP protocol at /mcp only.
# Inject / and /health so Railway/Render healthchecks get HTTP 200.
from starlette.routing import Route as _Route
from starlette.requests import Request as _Request
from starlette.responses import JSONResponse as _JSONResponse

async def _health(request: _Request) -> _JSONResponse:
    return _JSONResponse({
        "status": "ok",
        "service": "semantic-scholar-mcp",
        "auth": "authenticated" if os.environ.get("S2_API_KEY") else "unauthenticated"
    })

# Expose ASGI app at module level — uvicorn target: server:asgi_app
asgi_app = app.streamable_http_app()
asgi_app.routes.insert(0, _Route("/", _health))
asgi_app.routes.insert(1, _Route("/health", _health))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting S2 MCP Server (ARES Edition) on {host}:{port}")
    logger.info(f"Auth: {'authenticated' if os.environ.get('S2_API_KEY') else 'unauthenticated'}")
    uvicorn.run(asgi_app, host=host, port=port)
