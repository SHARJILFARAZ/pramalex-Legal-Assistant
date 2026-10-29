# PramaLex — Fresh Build

A new implementation for Tamil Nadu civil/property legal case management and source-grounded legal research.

## Architecture
- `frontend/`: React + TypeScript + Vite + Tailwind + Framer Motion + Lucide
- `backend/`: Spring Boot 3 / Java 21 REST API, Spring Security, JWT, JPA, MySQL
- `ai-service/`: FastAPI judgment retrieval and evidence-grounded analysis
- `scripts/`: real-data acquisition/normalization tools
- `data/`: fallback runtime data directory. On Windows, the default corpus location is `D:\\PramaLexData\\raw\\real_judgments.jsonl` so the app can run from C: while data lives on D:

## Requirements
- JDK 21, Maven 3.9+
- Node 20+ and npm
- Python 3.11+
- MySQL 8+

## Local setup
1. Create a MySQL database: `CREATE DATABASE pramalex;`
2. Copy `backend/.env.example` to `.env` or set the environment variables listed there.
3. Backend: `cd backend && mvn spring-boot:run`
4. AI service: `cd ai-service && python -m venv .venv`, activate it, `pip install -r requirements.txt`, then `uvicorn app.main:app --reload --port 8000`
5. Frontend: `cd frontend && npm install && npm run dev`

The app uses real authentication against the API. Public registration always creates a PUBLIC account. Lawyer access requires administrator verification. On first startup, the backend seeds local demo accounts documented in `docs/BOOTSTRAP_ADMIN.md`.

## Legal data status
The source-verified judgment corpus remains separate from the optional 1,000-record analysis demonstration dataset at `data/demo/`. The demonstration records are for UI/search/analysis workflow testing and must not be cited as court judgments. No demonstration records are mixed into `D:/PramaLexData/raw/real_judgments.jsonl`. Run the importer only after checking the upstream source terms and availability. On Windows, the importer defaults to `D:/PramaLexData/raw/real_judgments.jsonl` (up to 2,000 records by default, subject to source availability). The AI service reads that same path by default. Set `PRAMALEX_JUDGMENTS_PATH` to override it. The importer saves real full-text records with provenance, court, date and source URL, and reports the actual count. It does not promise 5,000 if the upstream source cannot provide them. A downloaded record is not equivalent to legal verification.

## Safety and correctness
This is legal research support, not a substitute for professional legal judgment. Source text and legal status must be checked before court use. No output should invent citations, quotes, bench details or procedural facts.

## Build the Tamil Nadu civil/property corpus (D: drive)

Use `BUILD-TAMIL-NADU-CORPUS.bat` on Windows with Python 3.11+ and internet access. It uses the published `vaquill/open-india-law` dataset and selects the Madras High Court Parquet file rather than scanning the entire national dataset. It reconstructs complete records by `case_id` and `chunk_index`, ranks candidate cases using civil/property terms, requires meaningful full text and a source URL, and writes a manifest. Default output is `D:\\PramaLexData\\raw\\real_judgments.jsonl`.

The builder is intentionally conservative: it refuses to replace an existing output unless at least 2,000 usable records are produced (or the requested target is lower than 2,000). It does not fabricate cases. It requires network access, may take time because the selected court file is large, and the result is a keyword-selected research corpus—not a legal verification of each judgment's ratio, precedential status, or applicability. The data compilation is CC BY 4.0; retain attribution to Open India Law and underlying source publishers. District/trial-court decisions are not included in this source.

To run local unit tests for the filtering helpers:

```powershell
cd scripts
py -m unittest test_tamil_nadu_property_corpus.py
```


## Optional 1,000-record analysis demonstration corpus
The structured file `data/demo/pramalex_corpus_1000.jsonl` is provided for review demonstrations of search, ranking, issue analysis, and evidence-gap outputs. It is separate from the authentic judgment corpus. For Windows storage outside the project, copy `data/demo/` to `D:\PramaLexData\demo\`. The genuine judgment importer and D: drive output remain unchanged.
