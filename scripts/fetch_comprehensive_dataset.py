#!/usr/bin/env python3
"""Import real Indian court judgments and report why records are rejected.

No synthetic records or fabricated source URLs are created. The upstream dataset schema
can change, so this importer handles common nested/alternate field names and emits
diagnostics when the source doesn't contain the required evidence.
"""
import argparse, json, re, sys
from pathlib import Path
from datasets import load_dataset, get_dataset_config_names

TARGET = "overthelex/indian-court-decisions"
DOMAINS = {
 "A_REVENUE": [r"\bpatta\b", r"\bchitta\b", r"\badangal\b", r"\btahsildar\b", r"\brevenue record", r"\bmutation\b"],
 "B_LAND_TYPES": [r"grama natham", r"\bnatham land", r"\bporamboke\b", r"\bnanjai\b", r"\bpunjai\b", r"land classification", r"\bencroachment\b"],
 "C_REGISTRATION": [r"registration act", r"registered sale deed", r"unregistered", r"\bsale deed\b", r"\bsettlement deed\b", r"section 22.?a", r"\bconveyance\b"],
 "D_CIVIL_REMEDIES": [r"\bpartition suit\b", r"\bpartition\b", r"specific performance", r"permanent injunction", r"declaration of title", r"\btrespass\b", r"\bco.?owner\b"],
 "E_HISTORICAL_POSSESSION": [r"adverse possession", r"ryotwari", r"estates abolition", r"historical possession", r"double sale", r"limitation act", r"long possession"]
}
COURT_PATTERNS = (r"madras", r"supreme court", r"district court", r"subordinate judge", r"civil court", r"high court")
ALIASES = {
 "title": ["cause_title","title","case_name","case_title","name","caseTitle","parties","case"],
 "court": ["court","court_name","bench","court_type","courtName","court_name_en","courtName"],
 "date": ["judgment_date","date","decision_date","judgmentDate","date_of_judgment","date_of_decision","decisionDate"],
 "citation": ["citation","citations","neutral_citation","case_citation","citation_number"],
 "text": ["full_text","judgment_text","text","content","judgment","body","document","judgmentText","judgment_content","html","raw_text"],
 "url": ["source_url","url","judgment_url","document_url","source","link","pdf_url","judgment_link","sourceLink"],
 "id": ["case_id","id","doc_id","document_id","caseId","documentId"]
}
def valstr(v):
    if v is None: return ""
    if isinstance(v, (str,int,float)): return str(v).strip()
    if isinstance(v, dict):
        for k in ("text","value","name","title","url","label"):
            if k in v and valstr(v[k]): return valstr(v[k])
        return ""
    if isinstance(v, list):
        return " ".join(filter(None,(valstr(x) for x in v)))
    return ""
def first(row, names):
    for n in names:
        if n in row:
            v=valstr(row.get(n))
            if v: return v
    return ""
def norm(row):
    # Flatten common metadata containers without overriding top-level values.
    merged=dict(row)
    for key in ("metadata","meta","case_metadata","document_metadata","data"):
        v=row.get(key)
        if isinstance(v,dict):
            for k,val in v.items(): merged.setdefault(k,val)
    vals={k:first(merged,names) for k,names in ALIASES.items()}
    if not vals["text"]:
        for k,v in merged.items():
            if any(t in k.lower() for t in ("judgment","fulltext","full_text","content","document_text")):
                vals["text"]=valstr(v)
                if len(vals["text"])>200: break
    if not vals["title"]: vals["title"]=" ".join(x for x in [vals["citation"], vals["id"]] if x)
    missing=[]
    if len(vals["text"]) < 200: missing.append("missing_or_short_text")
    if not vals["title"]: missing.append("missing_title")
    if not vals["court"]: missing.append("missing_court")
    elif not any(re.search(p,vals["court"],re.I) for p in COURT_PATTERNS): missing.append("court_not_recognized")
    if not vals["url"].startswith(("http://","https://")): missing.append("missing_source_url")
    if missing: return None, missing
    return {"cause_title":vals["title"],"citation":vals["citation"] or None,"court":vals["court"],
            "judgment_date":vals["date"] or None,"full_text":vals["text"],"source_url":vals["url"],
            "upstream_id":vals["id"] or None}, []
def category_for(text):
    low=text.lower()
    for cat, patterns in DOMAINS.items():
        if any(re.search(p,low,re.I) for p in patterns): return cat
    return None
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--per-category",type=int,default=400, help="Target per issue category (default 400 x 5 categories = up to 2000 records)")
    ap.add_argument("--scan-limit-per-config",type=int,default=500000)
    ap.add_argument("--output",default="D:/PramaLexData/raw/real_judgments.jsonl", help="Output JSONL path; default stores corpus on D: drive on Windows")
    ap.add_argument("--dataset",default=TARGET)
    ap.add_argument("--diagnostic-samples",type=int,default=5)
    args=ap.parse_args()
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    counts={k:0 for k in DOMAINS}; seen=set(); scanned=0
    rejects={}; samples=[]; sample_keys=[]
    try: configs=get_dataset_config_names(args.dataset)
    except Exception as e: print(f"Could not inspect dataset: {e}",file=sys.stderr);sys.exit(2)
    if not configs: configs=["default"]
    print(f"Dataset: {args.dataset}; configs={configs}; target={args.per_category*len(DOMAINS)}")
    with out.open("w",encoding="utf-8") as f:
      for config in configs:
        if all(v>=args.per_category for v in counts.values()): break
        try: stream=load_dataset(args.dataset,config,split="train",streaming=True)
        except Exception as e:
          print(f"Skipping config {config}: {e}",file=sys.stderr);continue
        for row in stream:
          scanned+=1
          if scanned%500==0: print(f"[Progress] scanned={scanned}; accepted={sum(counts.values())}; rejected={sum(rejects.values())}")
          if scanned>args.scan_limit_per_config: print("Per-config scan limit reached");break
          if not isinstance(row,dict):
              rejects["row_not_object"]=rejects.get("row_not_object",0)+1; continue
          if len(sample_keys)<1: sample_keys=list(row.keys())
          record, reasons=norm(row)
          if not record:
              for reason in reasons: rejects[reason]=rejects.get(reason,0)+1
              if len(samples)<args.diagnostic_samples:
                  samples.append({"keys":list(row.keys()),"reasons":reasons,
                                  "preview":{k:valstr(row.get(k))[:180] for k in list(row)[:12]}})
              continue
          key=record["source_url"].rstrip("/").lower()
          if key in seen:
              rejects["duplicate_url"]=rejects.get("duplicate_url",0)+1; continue
          cat=category_for(record["full_text"]+" "+record["cause_title"])
          if not cat:
              rejects["no_property_category_match"]=rejects.get("no_property_category_match",0)+1; continue
          if counts[cat]>=args.per_category:
              rejects["category_quota_reached"]=rejects.get("category_quota_reached",0)+1; continue
          seen.add(key);record["category"]=cat
          record["case_id"]=f"TN-PROP-{sum(counts.values())+1:05d}"
          record["summary_snippet"]=re.sub(r"\s+"," ",record["full_text"])[:700]
          f.write(json.dumps(record,ensure_ascii=False)+"\n")
          counts[cat]+=1
          if sum(counts.values())%50==0: print(f"[Progress] accepted={sum(counts.values())}; categories={counts}")
    result={"output":str(out),"records":sum(counts.values()),"category_counts":counts,
            "scanned":scanned,"rejected":sum(rejects.values()),"rejection_reasons":rejects,
            "source_fields_sample":sample_keys,"rejected_record_samples":samples}
    print(json.dumps(result,indent=2,ensure_ascii=False))
    if sum(counts.values()) < args.per_category*len(DOMAINS):
      print("SHORTFALL: upstream data did not provide the full target. No synthetic cases were created.",file=sys.stderr)
if __name__=="__main__": main()
