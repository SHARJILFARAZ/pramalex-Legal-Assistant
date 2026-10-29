# PramaLex Literature Map

After case analysis returns retrieved judgments, the analysis screen now includes a Literature Map / Judgment Relationship Explorer.

- Each returned judgment is an interactive node.
- Selecting a node updates the selected-judgment summary and opens the expanded case-details panel.
- List view provides an accessible alternative to the map.
- Filter by title, citation, issue or court.
- The map shows up to 40 retrieved results at once; all returned judgments remain listed below.
- Node colors distinguish retrieval-score bands and illustrative/non-authority records.
- Lines are visual navigation aids connecting the research focus to result nodes. They do not claim citation relationships, precedent, or legal similarity beyond the retrieval score.
- Original-source links are displayed only when returned by the API.
- Missing metadata is not fabricated; the existing Authority component displays "Not available in the retrieved record".

The map runs entirely in the frontend and does not require a new backend endpoint or database migration.
