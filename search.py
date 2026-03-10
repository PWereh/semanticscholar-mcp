import os
import requests
import time
import logging
from typing import List, Dict, Any, Optional

BASE_URL = "https://api.semanticscholar.org/graph/v1"
BASE_RECOMMENDATION_URL = "https://api.semanticscholar.org/recommendations/v1"

S2_API_KEY = os.environ.get("S2_API_KEY") or os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if S2_API_KEY:
    logger.info("S2 API key loaded — authenticated tier active")
else:
    logger.warning("S2_API_KEY not set — unauthenticated (shared rate limit)")


def _auth_headers() -> Dict[str, str]:
    return {"x-api-key": S2_API_KEY} if S2_API_KEY else {}


def make_request_with_retry(url, params=None, json_data=None, method="GET", max_retries=5, base_delay=1.0):
    headers = _auth_headers()
    for attempt in range(max_retries + 1):
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, params=params, json=json_data, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limit. Retry {attempt+1}/{max_retries} in {delay}s")
                    time.sleep(delay)
                    continue
                raise Exception("Rate limit exceeded")
            else:
                response.raise_for_status()
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt)); continue
            raise Exception("Timeout exhausted")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt)); continue
            raise Exception(f"Request failed: {e}")
    raise Exception("Retry logic error")


_PAPER_SEARCH_FIELDS = (
    "paperId,title,abstract,year,authors,url,venue,publicationVenue,"
    "publicationTypes,citationCount,influentialCitationCount,"
    "externalIds,openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,"
    "publicationDate,journal,tldr,isOpenAccess"
)
_PAPER_DETAIL_FIELDS = (
    "paperId,title,abstract,year,authors,url,venue,publicationVenue,"
    "publicationTypes,citationCount,referenceCount,influentialCitationCount,"
    "externalIds,openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,"
    "publicationDate,journal,citationStyles,tldr,isOpenAccess"
)
_CITATION_FIELDS = "contexts,isInfluential,intents,citingPaper.paperId,citingPaper.title,citingPaper.authors,citingPaper.year,citingPaper.venue,citingPaper.citationCount,citingPaper.externalIds"
_REFERENCE_FIELDS = "contexts,isInfluential,intents,citedPaper.paperId,citedPaper.title,citedPaper.authors,citedPaper.year,citedPaper.venue,citedPaper.citationCount,citedPaper.externalIds"
_AUTHOR_FIELDS = "authorId,name,url,affiliations,paperCount,citationCount,hIndex"
_RECOMMENDATION_FIELDS = (
    "paperId,corpusId,externalIds,url,title,abstract,venue,publicationVenue,"
    "year,referenceCount,citationCount,influentialCitationCount,isOpenAccess,"
    "openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,publicationTypes,"
    "publicationDate,journal,citationStyles,authors"
)


def _fmt_paper(p):
    if not p: return {}
    ext = p.get("externalIds") or {}
    oa = p.get("openAccessPdf") or {}
    return {
        "paperId": p.get("paperId"),
        "title": p.get("title"),
        "abstract": p.get("abstract"),
        "year": p.get("year"),
        "publicationDate": p.get("publicationDate"),
        "authors": [{"name": a.get("name"), "authorId": a.get("authorId")} for a in (p.get("authors") or [])],
        "journal": p.get("journal"),
        "venue": p.get("venue"),
        "publicationVenue": p.get("publicationVenue"),
        "publicationTypes": p.get("publicationTypes"),
        "fieldsOfStudy": p.get("fieldsOfStudy"),
        "s2FieldsOfStudy": p.get("s2FieldsOfStudy"),
        "citationCount": p.get("citationCount"),
        "referenceCount": p.get("referenceCount"),
        "influentialCitationCount": p.get("influentialCitationCount"),
        "isOpenAccess": p.get("isOpenAccess"),
        "openAccessPdfUrl": oa.get("url"),
        "externalIds": ext,
        "doi": ext.get("DOI"),
        "arxivId": ext.get("ArXiv"),
        "url": p.get("url"),
        "tldr": p.get("tldr"),
        "citationStyles": p.get("citationStyles"),
    }

def _fmt_author(a):
    if not a: return {}
    return {k: a.get(k) for k in ["authorId","name","url","affiliations","paperCount","citationCount","hIndex"]}


def search_papers(query, limit=10):
    try:
        data = make_request_with_retry(f"{BASE_URL}/paper/search",
            params={"query": query, "limit": min(limit, 100), "fields": _PAPER_SEARCH_FIELDS})
        return [_fmt_paper(p) for p in data.get("data", [])]
    except Exception as e:
        logger.error(f"search_papers: {e}"); return []

def search_paper_match(query):
    try:
        data = make_request_with_retry(f"{BASE_URL}/paper/search/match",
            params={"query": query, "fields": _PAPER_SEARCH_FIELDS})
        papers = data.get("data", [])
        if papers:
            r = _fmt_paper(papers[0]); r["matchScore"] = papers[0].get("matchScore"); return r
        return {"error": "No match found"}
    except Exception as e:
        return {"error": str(e)}

def get_paper_autocomplete(query):
    try:
        data = make_request_with_retry(f"{BASE_URL}/paper/autocomplete", params={"query": query[:100]})
        return [{"id": m.get("id"), "title": m.get("title"), "authorsYear": m.get("authorsYear")} for m in data.get("matches", [])]
    except Exception as e:
        logger.error(f"autocomplete: {e}"); return []

def get_paper_details(paper_id):
    try:
        data = make_request_with_retry(f"{BASE_URL}/paper/{paper_id}", params={"fields": _PAPER_DETAIL_FIELDS})
        return _fmt_paper(data)
    except Exception as e:
        return {"error": str(e)}

def get_papers_batch(paper_ids):
    if len(paper_ids) > 500: paper_ids = paper_ids[:500]
    try:
        data = make_request_with_retry(f"{BASE_URL}/paper/batch",
            params={"fields": _PAPER_DETAIL_FIELDS}, json_data={"ids": paper_ids}, method="POST")
        return [_fmt_paper(p) for p in data if p] if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"papers_batch: {e}"); return []

def get_paper_citations(paper_id, limit=50, influential_only=False):
    try:
        data = make_request_with_retry(f"{BASE_URL}/paper/{paper_id}/citations",
            params={"limit": min(limit, 1000), "fields": _CITATION_FIELDS})
        items = data.get("data", [])
        if influential_only: items = [c for c in items if c.get("isInfluential")]
        return [{"contexts": c.get("contexts",[]), "intents": c.get("intents",[]),
                 "isInfluential": c.get("isInfluential"), "citingPaper": _fmt_paper(c.get("citingPaper",{}))} for c in items]
    except Exception as e:
        logger.error(f"citations: {e}"); return []

def get_paper_references(paper_id, limit=100, influential_only=False):
    try:
        data = make_request_with_retry(f"{BASE_URL}/paper/{paper_id}/references",
            params={"limit": min(limit, 1000), "fields": _REFERENCE_FIELDS})
        items = data.get("data", [])
        if influential_only: items = [r for r in items if r.get("isInfluential")]
        return [{"contexts": r.get("contexts",[]), "intents": r.get("intents",[]),
                 "isInfluential": r.get("isInfluential"), "citedPaper": _fmt_paper(r.get("citedPaper",{}))} for r in items]
    except Exception as e:
        logger.error(f"references: {e}"); return []

def get_citations_and_references(paper_id):
    return {"citations": get_paper_citations(paper_id), "references": get_paper_references(paper_id)}

def search_snippets(query, limit=10):
    try:
        data = make_request_with_retry(f"{BASE_URL}/snippet/search",
            params={"query": query, "limit": min(limit, 1000),
                    "fields": "snippet.text,snippet.snippetKind,snippet.section,paper.corpusId,paper.title,paper.authors,paper.year,paper.externalIds"})
        return [{"score": i.get("score"),
                 "snippet": {"text": i.get("snippet",{}).get("text"), "kind": i.get("snippet",{}).get("snippetKind"), "section": i.get("snippet",{}).get("section")},
                 "paper": {"corpusId": i.get("paper",{}).get("corpusId"), "title": i.get("paper",{}).get("title"),
                           "year": i.get("paper",{}).get("year"), "doi": (i.get("paper",{}).get("externalIds") or {}).get("DOI"),
                           "authors": i.get("paper",{}).get("authors",[])}} for i in data.get("data", [])]
    except Exception as e:
        logger.error(f"snippets: {e}"); return []

def search_authors(query, limit=10):
    try:
        data = make_request_with_retry(f"{BASE_URL}/author/search",
            params={"query": query, "limit": min(limit, 100), "fields": _AUTHOR_FIELDS})
        return [_fmt_author(a) for a in data.get("data", [])]
    except Exception as e:
        logger.error(f"search_authors: {e}"); return []

def get_author_details(author_id):
    try:
        return _fmt_author(make_request_with_retry(f"{BASE_URL}/author/{author_id}", params={"fields": _AUTHOR_FIELDS}))
    except Exception as e:
        return {"error": str(e)}

def get_authors_batch(author_ids):
    if len(author_ids) > 1000: author_ids = author_ids[:1000]
    try:
        data = make_request_with_retry(f"{BASE_URL}/author/batch",
            params={"fields": _AUTHOR_FIELDS}, json_data={"ids": author_ids}, method="POST")
        return [_fmt_author(a) for a in data if a] if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"authors_batch: {e}"); return []

def get_paper_recommendations(paper_id, limit=10):
    try:
        data = make_request_with_retry(f"{BASE_RECOMMENDATION_URL}/papers/forpaper/{paper_id}",
            params={"limit": min(limit, 500), "fields": _RECOMMENDATION_FIELDS})
        return [_fmt_paper(p) for p in data.get("recommendedPapers", [])]
    except Exception as e:
        logger.error(f"recommendations: {e}"); return []

def get_paper_recommendations_from_lists(positive_paper_ids, negative_paper_ids=None, limit=10):
    payload = {"positivePaperIds": positive_paper_ids}
    if negative_paper_ids: payload["negativePaperIds"] = negative_paper_ids
    try:
        data = make_request_with_retry(f"{BASE_RECOMMENDATION_URL}/papers",
            params={"limit": min(limit, 500), "fields": _RECOMMENDATION_FIELDS},
            json_data=payload, method="POST")
        return [_fmt_paper(p) for p in data.get("recommendedPapers", [])]
    except Exception as e:
        logger.error(f"recommendations_from_lists: {e}"); return []
