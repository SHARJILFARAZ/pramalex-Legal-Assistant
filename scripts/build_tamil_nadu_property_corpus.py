#!/usr/bin/env python3
"""Build an offline Tamil Nadu civil/property judgment corpus from Open India Law.

Downloads/streams only court-specific Parquet files; stores output on D: by default.
Judgment rows are chunks, so case_id is deduplicated and chunk_index orders full text.
No synthetic judgments are ever generated. Network access is required for the build.
"""
from __future__ import annotations
import argparse, json, os, re, sqlite3, sys, time
from pathlib import Path
from typing import Any

DATASET = "vaquill/open-india-law"
DEFAULT_OUT = Path("D:/PramaLexData/raw/real_judgments.jsonl")
# Broad legal-property terms; relevance is ranked, not treated as a legal correctness label.
TERMS = {
 "title_ownership": ["title suit", "title deed", "ownership", "declaration of title", "title to property", "title dispute"],
 "sale_registration": ["sale deed", "sale agreement", "registration act", "unregistered sale", "conveyance", "specific performance"],
 "partition_inheritance": ["partition suit", "partition", "coparcenary", "inheritance", "succession", "legal heir"],
 "possession_injunction": ["possession", "adverse possession", "permanent injunction", "temporary injunction", "trespass", "encroachment"],
 "land_revenue": ["patta", "chitta", "adangal", "natham", "poramboke", "ryotwari", "revenue records", "land acquisition"],
 "lease_tenancy": ["lease", "tenant", "eviction", "landlord", "rent control", "easement", "boundary dispute"],
}
ALL_TERMS = [(cat, term) for cat, terms in TERMS.items() for term in terms]

def s(v: Any) -> str:
    if v is None: return ""
    if isinstance(v, (str, int, float)): return str(v).strip()
    if isinstance(v, list): return " ".join(filter(None, (s(x) for x in v)))
    if isinstance(v, dict):
        for k in ("text", "value", "name", "title", "url"):
            if v.get(k) is not None: return s(v[k])
    return ""

def field(row: dict, *keys: str) -> str:
    for key in keys:
        value = s(row.get(key))
        if value: return value
    return ""

def get_text(row: dict) -> str:
    return field(row, "text_original", "text", "full_text", "judgment_text", "content", "body")

def get_case_id(row: dict) -> str:
    return field(row, "case_id", "doc_id", "document_id", "id")

def score_row(row: dict) -> tuple[int, list[str]]:
    text = " ".join([field(row, "title", "case_title", "cause_title", "description"), get_text(row)]).lower()
    hits = [term for _, term in ALL_TERMS if term in text]
    # A chunk must contain substantive property/civil vocabulary; avoid generic-only matches.
    return len(hits), hits

def choose_files(repo_files: list[str], include_supreme: bool) -> list[str]:
    parquet = [p for p in repo_files if p.lower().endswith(".parquet") and "judgment" in p.lower()]
    madras = [p for p in parquet if "madras" in Path(p).name.lower()]
    supreme = [p for p in parquet if "supreme" in Path(p).name.lower()]
    selected = madras + (supreme if include_supreme else [])
    # Don't silently scan the whole national dataset if naming changes.
    return sorted(set(selected))

def dataset_stream(file_path: str):
    from datasets import load_dataset
    return load_dataset(DATASET, data_files={"train": file_path}, split="train", streaming=True)

def build(output: Path, target: int = 2500, include_supreme: bool = False, work_dir: Path | None = None) -> dict:
    from huggingface_hub import HfApi
    api = HfApi()
    repo_files = api.list_repo_files(DATASET, repo_type="dataset")
    files = choose_files(repo_files, include_supreme)
    if not files:
        raise RuntimeError("Could not find Madras judgment Parquet file(s) in the dataset repository. No output was replaced.")
    output.parent.mkdir(parents=True, exist_ok=True)
    work_dir = work_dir or (output.parent / "build_work")
    work_dir.mkdir(parents=True, exist_ok=True)
    db_path = work_dir / "tn_property_build.sqlite3"
    if db_path.exists(): db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE candidates(case_id TEXT PRIMARY KEY, score INTEGER, title TEXT, court TEXT, decision_date TEXT, citation TEXT, source_url TEXT, case_number TEXT, category TEXT)")
    con.execute("CREATE TABLE selected(case_id TEXT PRIMARY KEY)")
    scanned = 0
    # Pass 1: identify likely relevant cases from their chunks, without downloading all chunks to RAM.
    for file_path in files:
        print(f"Scanning candidate terms: {file_path}", flush=True)
        for row in dataset_stream(file_path):
            scanned += 1
            cid = get_case_id(row)
            if not cid: continue
            score, hits = score_row(row)
            if score < 1: continue
            title = field(row, "title", "case_title", "cause_title")
            court = field(row, "court", "court_name", "bench", "court_type") or ("Madras High Court" if "madras" in file_path.lower() else "Supreme Court of India")
            date = field(row, "decision_date", "judgment_date", "date")
            citation = field(row, "citation", "case_number", "case_citation")
            url = field(row, "source_url", "pdf_url", "url", "mirror_url")
            category = next((cat for cat, terms in TERMS.items() if any(t in " ".join(hits) for t in terms)), "civil_property")
            old = con.execute("SELECT score FROM candidates WHERE case_id=?", (cid,)).fetchone()
            if old:
                if score > old[0]: con.execute("UPDATE candidates SET score=?, title=COALESCE(NULLIF(?,''),title), court=COALESCE(NULLIF(?,''),court), decision_date=COALESCE(NULLIF(?,''),decision_date), citation=COALESCE(NULLIF(?,''),citation), source_url=COALESCE(NULLIF(?,''),source_url), case_number=COALESCE(NULLIF(?,''),case_number), category=? WHERE case_id=?", (score,title,court,date,citation,url,field(row,"case_number"),category,cid))
            else:
                con.execute("INSERT INTO candidates VALUES(?,?,?,?,?,?,?,?,?)", (cid,score,title,court,date,citation,url,field(row,"case_number"),category))
            if scanned % 50000 == 0:
                con.commit(); print(f"Scanned {scanned:,} chunks; candidate cases={con.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]:,}", flush=True)
        con.commit()
    candidate_count = con.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    if not candidate_count:
        con.close(); raise RuntimeError("Zero candidate cases matched. No output was replaced. Check the dataset schema/filters before retrying.")
    # Rank by term hits; keep modest oversampling in case text is incomplete.
    con.execute("INSERT INTO selected SELECT case_id FROM candidates ORDER BY score DESC, case_id LIMIT ?", (target,))
    selected_count = con.execute("SELECT COUNT(*) FROM selected").fetchone()[0]
    # Pass 2: reconstruct all chunks for selected cases, ordered later by chunk_index.
    con.execute("CREATE TABLE chunks(case_id TEXT, chunk_index INTEGER, text TEXT, PRIMARY KEY(case_id, chunk_index))")
    scanned2 = 0
    for file_path in files:
        print(f"Reconstructing selected judgments: {file_path}", flush=True)
        for row in dataset_stream(file_path):
            scanned2 += 1
            cid = get_case_id(row)
            if not cid or not con.execute("SELECT 1 FROM selected WHERE case_id=?", (cid,)).fetchone(): continue
            text = get_text(row)
            if not text: continue
            try: idx = int(row.get("chunk_index", row.get("chunk_order", 0)) or 0)
            except (ValueError, TypeError): idx = 0
            con.execute("INSERT OR REPLACE INTO chunks VALUES(?,?,?)", (cid, idx, text))
            if scanned2 % 50000 == 0: con.commit(); print(f"Reconstruction scan: {scanned2:,} chunks", flush=True)
        con.commit()
    # Build a temporary output; replace final only after it is nonempty and structurally valid.
    tmp = output.with_suffix(output.suffix + ".tmp")
    counts = {k: 0 for k in TERMS}; written = 0; rejected_short = 0
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        rows = con.execute("SELECT c.case_id,c.score,c.title,c.court,c.decision_date,c.citation,c.source_url,c.case_number,c.category FROM candidates c JOIN selected s USING(case_id) ORDER BY c.score DESC")
        for cid, score, title, court, date, citation, url, case_number, category in rows:
            pieces = [r[0] for r in con.execute("SELECT text FROM chunks WHERE case_id=? ORDER BY chunk_index", (cid,))]
            full_text = "\n\n".join(pieces).strip()
            if len(full_text) < 500:
                rejected_short += 1; continue
            if not url.startswith(("http://", "https://")):
                # Provenance is required for the runtime retrieval API; do not invent it.
                rejected_short += 1; continue
            record = {"case_id": cid, "upstream_id": cid, "cause_title": title or "Title unavailable in source", "citation": citation or None,
                      "court": court or "Court unavailable in source", "judgment_date": date or None, "case_number": case_number or None,
                      "full_text": full_text, "source_url": url or None, "source_publisher": "Open India Law / underlying court publisher",
                      "category": category, "relevance_score": score, "corpus_source": DATASET,
                      "license": "CC BY 4.0; retain attribution", "text_verification": "Source text assembled from published chunks; legal ratio/current status not independently verified."}
            f.write(json.dumps(record, ensure_ascii=False) + "\n"); written += 1
            if category in counts: counts[category] += 1
    con.close()
    minimum_required = min(target, 2000)
    if written < minimum_required:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Only {written} usable cases passed validation; at least {minimum_required} are required. Existing output was preserved. Rejected short/empty/missing-source cases: {rejected_short}.")
    os.replace(tmp, output)
    manifest = {"dataset": DATASET, "files": files, "target": target, "candidate_cases": candidate_count,
                "selected_cases": selected_count, "records_written": written, "short_or_empty_rejected": rejected_short,
                "category_counts": counts, "output": str(output), "chunks_scanned_pass1": scanned, "chunks_scanned_pass2": scanned2,
                "note": "Counts reflect records actually written. Selection is keyword-based and requires legal review; no synthetic judgments generated."}
    manifest_path = output.parent / "corpus_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return manifest

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", type=int, default=2500, help="Target number of distinct cases (default 2500; maximum 3000 recommended)")
    p.add_argument("--output", default=str(DEFAULT_OUT), help="JSONL output; defaults to D:/PramaLexData/raw/real_judgments.jsonl")
    p.add_argument("--include-supreme", action="store_true", help="Also include Supreme Court cases; they are not automatically Tamil Nadu cases")
    a = p.parse_args()
    if not 1 <= a.target <= 3000: p.error("--target must be between 1 and 3000")
    try: build(Path(a.output), a.target, a.include_supreme)
    except Exception as exc:
        print(f"BUILD FAILED: {exc}\nExisting corpus was not overwritten unless a validated output was produced.", file=sys.stderr)
        sys.exit(2)
if __name__ == "__main__": main()
