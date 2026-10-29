# PramaLex AI output and corpus audit

## Changes in this update

- AI service can load the configured D: corpus, a bundled real corpus, or the bundled demonstration corpus without requiring code edits.
- Exact duplicate JSON records are skipped at load time and the corpus status endpoint reports the number skipped.
- Retrieval results avoid repeated identical text and repeated titles within one response.
- Results expose source classification, topic/issue, matched query terms, and a source URL only when one is present and the record is not classified as an illustrative scenario.
- Case Cut has a more useful 11-section structure for facts, issues, retrieved material, document checklist, argument prompts, and verification gaps.
- Missing judgment details are not fabricated. The report explicitly avoids inventing a holding or disposal order.

## Corpus findings for the bundled JSONL

- Physical JSONL records: 1,000.
- Unique case IDs: 1,000.
- Exact unique JSON objects: 1,000.
- `record_origin` values: all 1,000 are `demonstration_scenario`.
- Unique JSON records do not imply 1,000 unique, independently sourced judgments. The records use templated text and do not contain traceable judgment URLs.

## Validation performed

- Python syntax compilation passed.
- AI service tests passed: 5 tests.
- This does not constitute a full live end-to-end test of the frontend, Spring Boot API, MySQL, document upload, or PDF export.

## Legal-use limitation

Illustrative records are not court authorities. For legal research, load authentic judgment text with a traceable source URL and verify the judgment, exact ratio, subsequent treatment, and current legal applicability before relying on it.
