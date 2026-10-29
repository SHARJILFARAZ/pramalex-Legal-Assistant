# Separate corpus indexing change

The Madras candidate collection now uses `HashingVectorizer` instead of fitting a large TF-IDF vocabulary over all long records. This avoids the expensive vocabulary-fit step during startup and `/reload`. For the candidate index only, derived search text is capped at 12,000 characters per record; original JSONL records are not rewritten. The existing collection still uses its original TF-IDF index and remains separate.

After replacing the project with this ZIP, restart the FastAPI service and check `GET /corpus/status`. Candidate count is reported under `separate_collections.madras.records`. Do not repeatedly call `/reload` while a prior request is still processing.

## Corpus selection in casework

The My Cases workspace includes a corpus selector used by both Analyse Case and Generate Case Cut. The backend forwards the selected collection to the AI service as `dataset=existing` or `dataset=madras`. Legal Research already uses the same dataset parameter. Demo scenario records remain in the bundled file for local testing but are filtered out of judgment search results so they are not presented as real court decisions.

The extracted Madras candidate JSONL is read-only. It remains separate from the bundled 1,000-record collection. Candidate records without a source URL can be retrieved for research exploration, but they must not be described as source-verified authorities.


## Retrieval integration correction

- Search no longer collapses all records with a missing title into a single generic-title result. Exact duplicate text is still de-duplicated.
- `/analyse` and `/case-cut` retain retrieved records even when a source URL is absent; source-linked authority counts remain separate.
- Original and Madras collections remain separately selected with `dataset=existing` and `dataset=madras`. Source JSONL records are not rewritten.
- The UI calls these items “retrieved records,” not authorities, unless source verification has been performed.
- Run `python -m pytest app/test_main.py -q` from `ai-service` to check the retrieval regression tests.
