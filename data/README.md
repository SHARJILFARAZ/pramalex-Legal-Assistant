Runtime judgment data belongs here as `real_judgments.jsonl`. It is deliberately not populated with fake legal cases. Run `scripts/fetch_comprehensive_dataset.py` to attempt acquisition from the configured upstream dataset, after reviewing source terms. A partial count is possible and must be disclosed.


## Separate Madras land corpus
Place `madras_land_candidates.jsonl` in `data/candidates/`, or set `PRAMALEX_CANDIDATE_JUDGMENTS_PATH` to its full path. This collection is indexed separately from the existing bundled 1,000-record collection and can be selected independently in Legal Research. The loader adds derived text only in memory; it does not rewrite source records. Records without a source URL remain searchable, and no source URL is fabricated.
