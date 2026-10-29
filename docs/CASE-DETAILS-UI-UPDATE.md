# PramaLex expandable judgment details update

## Changes
- Relevant judgment cards now show a summary, match score, court, citation/date, issue and district/context tags.
- Each card has a **View full case details** control that expands field-wise details: case title/number, court/bench, date, district, parties, judge/counsel names when present, statutes, questions/legal issues, evidence/documents, analysis/reasoning, outcome, retrieved passage, and original-source link.
- Missing details are explicitly labelled as unavailable rather than fabricated.
- Illustrative demo scenarios are labelled as illustrative and not real court judgments. They have no binding citation and should not be represented as actual judgments.
- FastAPI research results now return structured source fields needed by the expanded UI when those fields exist in the underlying corpus.
- Fixed the Java `caseView()` oversized `Map.of()` call by using `LinkedHashMap` and fixed `safeCorpus()` generic map conversion.

## Validation
- AI service tests: 5 passed.
- Frontend build was attempted but dependency installation did not complete within the execution time limit.
- Maven compilation could not be run in this environment because Maven is not installed.

Run locally:
- Frontend: `cd frontend`, `npm install`, `npm run build`
- Backend: `cd backend`, `mvn clean compile`
- AI service: `cd ai-service`, `python -m pytest -q`

The UI only displays judge, counsel, statutes, evidence and outcome details if the record provides them. It intentionally does not invent missing legal metadata.
