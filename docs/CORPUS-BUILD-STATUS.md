# Corpus build status

This package contains a revised corpus builder for `vaquill/open-india-law`.

## Verified in this environment
- Python syntax compilation passed for the builder and its tests.
- Three unit tests passed for court-file selection, chunk field extraction, property-term matching, and rejection of a non-property example.
- The builder defaults to `D:/PramaLexData/raw/real_judgments.jsonl` and writes a manifest beside the corpus.
- The builder writes to a temporary file and refuses to replace the final corpus unless at least 2,000 records (or the lower requested target) have meaningful reconstructed text and an HTTP(S) source URL.

## Not verified here
- A live Hugging Face download and a full corpus build could not be run because this environment has no DNS/network access to the dataset host.
- Therefore this ZIP does not include the 2,000–3,000 judgment records and does not claim that the full target has been reached.

## Data and legal limitations
- Source: Open India Law (`vaquill/open-india-law`), data compilation CC BY 4.0; preserve attribution and source provenance.
- The public judgment dataset contains chunks, not one complete judgment per row. The builder groups by `case_id` and orders chunks by `chunk_index`.
- Keyword selection identifies likely civil/property material; it is not a legal opinion or verification of ratio, current precedent status, or applicability.
- The source does not include district and trial court decisions.
