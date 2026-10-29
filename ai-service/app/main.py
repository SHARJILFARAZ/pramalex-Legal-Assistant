from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import HashingVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUNDLED_DEMO = PROJECT_ROOT / "data" / "demo" / "pramalex_corpus_1000.jsonl"
BUNDLED_REAL = PROJECT_ROOT / "data" / "real_judgments.jsonl"
D_DEMO = Path("D:/PramaLexData/demo/pramalex_demo_corpus_1000.jsonl")
D_REAL = Path("D:/PramaLexData/raw/real_judgments.jsonl")
# The Vaquill/Madras corpus is a separate collection; it never replaces the existing 1,000-record file.
CANDIDATE_DEFAULT = PROJECT_ROOT / "data" / "candidates" / "madras_land_candidates.jsonl"
CANDIDATE_PATH = Path(os.getenv("PRAMALEX_CANDIDATE_JUDGMENTS_PATH", str(CANDIDATE_DEFAULT))).expanduser()

# Explicit environment configuration wins. Otherwise prefer a real corpus if one
# exists, then the D: demo file, then the bundled demo file for portable testing.
_configured = os.getenv("PRAMALEX_JUDGMENTS_PATH")
if _configured:
    DATA_PATH = Path(_configured).expanduser().resolve()
elif D_REAL.exists() and D_REAL.stat().st_size:
    DATA_PATH = D_REAL
elif BUNDLED_REAL.exists() and BUNDLED_REAL.stat().st_size:
    DATA_PATH = BUNDLED_REAL
elif D_DEMO.exists():
    DATA_PATH = D_DEMO
else:
    DATA_PATH = BUNDLED_DEMO

app = FastAPI(
    title="PramaLex Legal Intelligence",
    version="1.1.0",
    description="Legal research retrieval and structured Case Cut support. Verify every authority against its original source.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

records: list[dict[str, Any]] = []
vectorizer = None
matrix = None
load_stats: dict[str, Any] = {}
candidate_records: list[dict[str, Any]] = []
candidate_vectorizer = None
candidate_matrix = None
candidate_stats: dict[str, Any] = {}


def _record_text(r: dict[str, Any]) -> str:
    parts = [r.get(k) for k in (
        "full_text", "text", "judgment_text", "judgment", "judgment_content",
        "document_text", "content", "source_excerpt", "summary_snippet",
        "title", "case_title", "cause_title", "case_name", "case_number",
        "citation", "court", "topic", "legal_issue", "facts_summary",
        "questions_for_determination", "key_concepts", "analysis_text",
        "outcome_text", "disposition", "matched_terms", "topic_categories"
    )]
    flattened: list[str] = []
    for value in parts:
        if isinstance(value, list):
            flattened.extend(str(x) for x in value if x)
        elif isinstance(value, dict):
            flattened.extend(str(x) for x in value.values() if x)
        elif value:
            flattened.append(str(value))
    # Keep order while removing repeated fragments.
    unique = list(dict.fromkeys(x.strip() for x in flattened if x and x.strip()))
    return " ".join(unique).strip()


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def load_records() -> None:
    global records, vectorizer, matrix, load_stats
    records = []
    exact_hashes: set[str] = set()
    rejected = 0
    exact_duplicates = 0
    origin_counts: dict[str, int] = {}
    if DATA_PATH.exists():
        with DATA_PATH.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                    if not isinstance(r, dict):
                        rejected += 1
                        continue
                    text = _record_text(r)
                    # Real legal authorities must have traceable source URLs.
                    # Illustrative records are searchable, but never represented as authorities.
                    origin = str(r.get("record_origin") or "").lower()
                    is_demo = origin in {"demonstration_scenario", "demo", "illustrative_scenario"} or str(r.get("case_id", "")).startswith("DEMO-")
                    if not text or (not is_demo and not r.get("source_url")):
                        rejected += 1
                        continue
                    canonical = json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                    if digest in exact_hashes:
                        exact_duplicates += 1
                        continue
                    exact_hashes.add(digest)
                    r["full_text"] = text
                    r["_is_demo"] = is_demo
                    r["_normalised_text"] = _normalise(text)
                    r["_origin"] = "demonstration_scenario" if is_demo else "external_source"
                    # Keep topic/issue separate so titles are not accidentally rendered as generic text fragments.
                    records.append(r)
                    origin_counts[r["_origin"]] = origin_counts.get(r["_origin"], 0) + 1
                except (json.JSONDecodeError, TypeError, ValueError):
                    rejected += 1
    if records:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=300000, sublinear_tf=True)
        matrix = vectorizer.fit_transform([str(r.get("full_text", ""))[:250000] for r in records])
    else:
        vectorizer = matrix = None
    load_stats = {
        "path": str(DATA_PATH), "records_loaded": len(records),
        "exact_duplicate_records_skipped": exact_duplicates,
        "invalid_or_untraceable_records_skipped": rejected,
        "origin_counts": origin_counts,
    }


load_records()


def load_candidate_records() -> None:
    """Load the extracted corpus independently without rewriting its source records."""
    global candidate_records, candidate_vectorizer, candidate_matrix, candidate_stats
    candidate_records = []
    hashes: set[str] = set()
    rejected = duplicates = 0
    if CANDIDATE_PATH.exists() and CANDIDATE_PATH.is_file():
        with CANDIDATE_PATH.open(encoding="utf-8-sig") as stream:
            for line in stream:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        rejected += 1
                        continue
                    text = _record_text(record)
                    if not text:
                        rejected += 1
                        continue
                    canonical = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                    if digest in hashes:
                        duplicates += 1
                        continue
                    hashes.add(digest)
                    # Keep all original keys/values intact; retrieval text and normalized text live only in memory.
                    indexed = dict(record)
                    indexed["full_text"] = text
                    indexed["_is_demo"] = False
                    indexed["_origin"] = "madras_land_corpus"
                    candidate_records.append(indexed)
                except (json.JSONDecodeError, TypeError, ValueError):
                    rejected += 1
    if candidate_records:
        # HashingVectorizer avoids a costly vocabulary-building fit over ~100k long
        # judgments. The source JSONL remains untouched; only derived index text is
        # capped to keep startup/reload memory and latency bounded.
        candidate_vectorizer = HashingVectorizer(
            stop_words="english", ngram_range=(1, 2), n_features=2**18,
            alternate_sign=False, norm="l2", lowercase=True,
        )
        index_texts = [str(r.get("full_text", ""))[:12000] for r in candidate_records]
        candidate_matrix = candidate_vectorizer.transform(index_texts)
    else:
        candidate_vectorizer = candidate_matrix = None
    candidate_stats = {"path": str(CANDIDATE_PATH), "records_loaded": len(candidate_records), "invalid_records_skipped": rejected, "exact_duplicate_records_skipped": duplicates}


load_candidate_records()


class QueryInput(BaseModel):
    query: str = Field(min_length=3, max_length=12000)
    case_id: int | None = None
    category: str = "PROPERTY"
    court: str | None = None
    district: str | None = None
    report: str | None = None
    dataset: str = Field(default="existing", pattern="^(existing|madras)$")


def _title(r: dict[str, Any]) -> str:
    for key in ("cause_title", "case_title", "title", "case_name"):
        value = r.get(key)
        if value and str(value).strip():
            return str(value).strip()
    # If the source has no title, use its supplied identifier as a neutral
    # display fallback so different records remain distinguishable in the UI.
    identifier = r.get("case_number") or r.get("case_id")
    return f"Record {identifier}" if identifier else "Case title unavailable"


def search(query: str, limit: int = 8, dataset: str = "existing") -> list[dict[str, Any]]:
    # Dataset selection is strict: each request searches only the chosen collection.
    if dataset == "madras":
        active_records, active_vectorizer, active_matrix = candidate_records, candidate_vectorizer, candidate_matrix
    else:
        active_records, active_vectorizer, active_matrix = records, vectorizer, matrix
    if not active_records or active_vectorizer is None or active_matrix is None:
        return []

    qv = active_vectorizer.transform([query])
    sims = cosine_similarity(qv, active_matrix).ravel()
    stop_terms = {"about","after","against","also","among","been","being","both","could","does","from","have","into","more","most","other","over","same","should","such","than","that","their","there","these","they","this","those","through","under","upon","very","were","what","when","where","which","while","with","would","your","case","court","judgment","legal","property","applicant","respondent","seeks"}
    raw_terms = re.findall(r"[a-zA-Z]{3,}", query.lower())
    query_terms = list(dict.fromkeys(t for t in raw_terms if t not in stop_terms))[:100]

    # Blend vector similarity with keyword overlap in judgment text and metadata.
    scored = []
    for i, r in enumerate(active_records):
        text = str(r.get("full_text") or _record_text(r))
        metadata = " ".join(str(r.get(k) or "") for k in ("title","cause_title","case_title","case_name","case_number","citation","petitioner","respondent","parties","topic","matched_terms","topic_categories")).lower()
        lower = text.lower()
        searchable = lower + " " + metadata
        hits = [t for t in query_terms if t in searchable]
        lexical = len(hits) / max(1, len(query_terms))
        cosine = float(sims[i])
        scored.append((cosine + 0.35 * lexical, cosine, hits, i, text, lower))
    # The Madras source is already a property-focused candidate collection. When
    # strict overlap is absent, return its top-ranked records rather than an empty
    # result; the UI displays these as retrieval leads, not confirmed authorities.
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

    out: list[dict[str, Any]] = []
    seen_fingerprints: set[str] = set()
    seen_titles: set[str] = set()
    for combined, score, hits, i, text, lower in scored:
        r = active_records[i]
        norm = str(r.get("_normalised_text") or _normalise(text))
        title = _title(r)
        fingerprint = hashlib.sha1(norm.encode("utf-8")).hexdigest()
        meaningful_title = title.casefold() != "case title unavailable"
        if fingerprint in seen_fingerprints or (meaningful_title and title.casefold() in seen_titles):
            continue
        seen_fingerprints.add(fingerprint)
        if meaningful_title:
            seen_titles.add(title.casefold())
        pos_candidates = [lower.find(t) for t in hits if lower.find(t) >= 0]
        pos = min(pos_candidates, default=0)
        start, end = max(0, pos - 220), min(len(text), pos + 900)
        is_demo = bool(r.get("_is_demo"))
        out.append({
            "case_id": r.get("case_id"),
            "cause_title": title,
            "record_origin": r.get("record_origin"),
            "citation": r.get("citation") or r.get("case_number"),
            "court": r.get("court") or r.get("court_context"),
            "judgment_date": r.get("judgment_date") or r.get("decision_date") or (str(r.get("decision_year") or r.get("year")) if (r.get("decision_year") or r.get("year")) else None),
            "source_url": r.get("source_url") if not is_demo else None,
            "relevant_statutes": r.get("relevant_statutes", []) if isinstance(r.get("relevant_statutes", []), list) else [],
            "similarity": round(score, 4),
            "source_excerpt": text[start:end],
            "excerpt_note": "Retrieved text; confirm missing details from the original source where available.",
            "dataset": dataset,
            "topic": r.get("topic"),
            "legal_issue": r.get("legal_issue"),
            "district_context": r.get("district_context"),
            "case_number": r.get("case_number"),
            "parties": r.get("parties") or {"claimant": r.get("petitioner"), "respondent": r.get("respondent")},
            "facts_summary": r.get("facts_summary"),
            "questions_for_determination": r.get("questions_for_determination", []),
            "key_concepts": r.get("key_concepts", []),
            "analysis_text": r.get("analysis_text"),
            "outcome_text": r.get("outcome_text") or r.get("disposition"),
            "evidence_used": r.get("evidence_used", r.get("documents_considered", [])),
            "judges": r.get("judges", r.get("judge")),
            "lawyers": r.get("lawyers", r.get("counsel", r.get("advocates"))),
            "relevance_terms": hits[:12],
        })
        if len(out) >= limit:
            break
    return out


@app.get("/health")
def health():
    return {"status": "UP", "service": "pramalex-ai", "records_loaded": len(records), "data_path": str(DATA_PATH)}


@app.get("/corpus/status")
def corpus_status():
    demo_count = sum(bool(r.get("_is_demo")) for r in records)
    real_count = len(records) - demo_count
    return {
        "status": "LOADED" if records else "EMPTY",
        "records": len(records),
        "full_text_records": sum(bool(r.get("full_text")) for r in records),
        "existing_collection_records": demo_count,
        "source_linked_records": real_count,
        "data_path": str(DATA_PATH),
        "mode": "mixed" if demo_count and real_count else ("demo" if demo_count else "real" if real_count else "empty"),
        "duplicate_check": {"exact_duplicate_records_skipped": load_stats.get("exact_duplicate_records_skipped", 0), "loaded_records_have_unique_case_ids": len({str(r.get("case_id")) for r in records}) == len(records)},
        "separate_collections": {"existing": {"records": len(records), "path": str(DATA_PATH)}, "madras": {"records": len(candidate_records), "path": str(CANDIDATE_PATH)}},
        "note": "Retrieval similarity and record availability do not establish legal applicability. Confirm the original source and current legal status before relying on a result.",
    }


@app.post("/reload")
def reload_corpus():
    load_records()
    load_candidate_records()
    return corpus_status()


@app.get("/research")
def research(q: str = Query(min_length=3, max_length=12000), limit: int = Query(default=8, ge=1, le=20), dataset: str = Query(default="existing", pattern="^(existing|madras)$")):
    results = search(q, limit, dataset=dataset)
    stats = load_stats if dataset == "existing" else candidate_stats
    return {"query": q, "dataset": dataset, "dataset_records": stats.get("records_loaded", len(records) if dataset == "existing" else len(candidate_records)), "count": len(results), "results": results,
            "status": "OK" if results else "NO_MATCHES_OR_DATASET_EMPTY",
            "disclaimer": "Search results are research leads. Check the original judgment and its current legal status before relying on it."}


@app.post("/analyse")
def analyse(payload: QueryInput):
    results = search(payload.query, 10, dataset=payload.dataset)
    # Retrieval results are shown even when a source URL is absent. The UI and
    # report expose source links only when present; absence must not erase a result.
    authorities = [r for r in results if r.get("source_url")]
    acts: dict[str, int] = {}
    for r in results:
        for act in r.get("relevant_statutes", []):
            acts[act] = acts.get(act, 0) + 1
    return {
        "case_id": payload.case_id, "query": payload.query, "retrieved_cases": results,
        "count": len(results), "source_linked_results": len(authorities), "other_results": len(results) - len(authorities),
        "potential_statutes": [{"name": k, "retrieval_count": v, "status": "candidate—verify against judgment"} for k, v in sorted(acts.items(), key=lambda x: -x[1])],
        "document_plan": {
            "potentially_relevant": ["Root and parent title deeds and complete chain of title", "Encumbrance Certificate for the relevant period", "Patta/chitta/adangal and mutation orders, where relevant", "Possession, boundary and survey records", "Agreements, notices, pleadings and prior orders"],
            "previous_judgment_evidence": "Do not state that a court relied on a document unless that is confirmed in the original judgment.",
            "missing_case_inputs": ["Exact relief sought and pleaded issues", "Complete title chain and dates", "Possession history", "Pending proceedings and prior orders", "Original documents and registration particulars"],
        },
        "hearing_preparation": {
            "supporting_points": "Potential issues to examine: execution and registration of the competing documents, consideration, possession, limitation, admissibility, and relief-specific requirements. Apply only after checking the actual pleadings and governing law.",
            "counterarguments": ["Test the opposing chain of title and document admissibility", "Check limitation and maintainability", "Distinguish title evidence from revenue entries", "Check whether the requested relief matches the proved facts"],
            "warning": "This is issue-spotting, not a legal conclusion or outcome prediction.",
        },
        "limitations": [
            "Similarity is a retrieval score, not a legal relevance or authority-strength score.",
            "A retrieved record without a source URL is shown as a research lead, not as a source-linked authority.",
            "Verify bench, exact ratio, later treatment, current law and original source before relying on a case.",
        ],
    }


@app.post("/case-cut")
def case_cut(payload: QueryInput):
    results = search(payload.query, 10, dataset=payload.dataset)
    authorities = [r for r in results if r.get("source_url")]
    top = results[0] if results else {}
    facts = payload.query.strip()
    metadata = {
        "Case Name": _title(top) if top else "Not available from retrieved material",
        "Citation": top.get("citation", "Not available from retrieved material") if top else "Not available from retrieved material",
        "Court": top.get("court", "Not verified") if top else "Not verified",
        "Judgment date": top.get("judgment_date", "Not available") if top else "Not available",
        "Source URL": top.get("source_url") or "No source URL is present in the retrieved record",
        "Source availability": "Source URL present; confirm the original judgment" if top.get("source_url") else "No source URL is present in this retrieved record",
    }
    issues = [
        "What legal effect follows from the competing documents, considering their execution, registration and admissibility?",
        "What evidence establishes title and possession, and what is the relevance of revenue records?",
        "Are limitation, maintainability and the relief sought supported by the pleadings and dates?",
    ]
    sections = [
        {"heading": "1. CASE IDENTIFICATION & SOURCE", "items": metadata},
        {"heading": "2. EXECUTIVE SUMMARY", "text": "This report organizes the supplied dispute facts and retrieved research leads. It does not determine title or predict the outcome. The source status of each retrieved item is shown separately."},
        {"heading": "3. FACTS PROVIDED FOR REVIEW", "text": "Facts supplied by the user; not independently verified.", "current_case_query": facts},
        {"heading": "4. ISSUES FOR DETERMINATION", "items": issues},
        {"heading": "5. RETRIEVED MATERIAL & RELEVANCE", "items": [{"case": r.get("cause_title"), "excerpt": r.get("source_excerpt"), "source_url": r.get("source_url"), "differences": "Matched query terms: " + (", ".join(r.get("relevance_terms", [])) or "No explicit query terms"), "note": "Check the original judgment and legal context before relying on this result."} for r in results]},
        {"heading": "6. HOLDING / DISPOSAL", "text": "No verified holding or disposal order can be stated from the current retrieved material. Do not infer a court's decision from a scenario description or search excerpt."},
        {"heading": "7. QUOTATION & PARAGRAPH REFERENCES", "text": "No quotation is marked as verified. Add a quotation only after checking the original judgment text and paragraph number."},
        {"heading": "8. COMPARISON MATRIX", "items": [{"case": r.get("cause_title"), "citation": r.get("citation"), "court": r.get("court"), "date": r.get("judgment_date"), "similarity": r.get("similarity"), "differences": "Query overlap: " + (", ".join(r.get("relevance_terms", [])) or "Not identified"), "source_url": r.get("source_url"), "record_origin": r.get("record_origin")} for r in results]},
        {"heading": "9. DOCUMENTS & EVIDENCE CHECKLIST", "items": ["Registered sale deed and certified copy, including schedules", "Prior title deeds and complete chain of title", "Encumbrance Certificate for the relevant period", "Patta/chitta/adangal and mutation orders, where relevant", "Survey sketch, boundary and possession evidence", "Competing agreement, payment proof, notices and pleadings", "Prior orders and case-status documents, if any"]},
        {"heading": "10. ARGUMENTS TO INVESTIGATE", "items": ["Compare execution, registration, consideration and admissibility of each document", "Test the chronology, possession evidence and chain of title", "Check limitation, maintainability and whether the relief matches the pleaded facts", "Identify adverse authorities and distinguish them using their actual facts and holdings"]},
        {"heading": "11. GAPS, RISKS & VERIFICATION", "items": ["Confirm original documents and property identity", "Verify every cited authority, source passage, bench, date and subsequent treatment", "Do not treat revenue entries alone as conclusive proof of title", "Separate factual evidence from assumptions and legal submissions", "Have a qualified lawyer review the report before use in proceedings"]},
    ]
    return {
        "title": "CASE SYNOPSIS & LAW POINT REPORT", "case_id": payload.case_id,
        "sections": sections, "authorities": results,
        "source_authority_count": len(authorities), "retrieved_record_count": len(results),
        "generated_at_note": "Generated from the currently loaded corpus and user-supplied facts; metadata and legal propositions require source verification.",
        "disclaimer": "Research support only. Confirm original judgments, legal propositions, current precedential status and applicability before court use.",
    }
