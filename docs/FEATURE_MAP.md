# Role / feature map

## Public
- Dashboard
- Legal research over the loaded public judgment index
- View result metadata, source excerpt and source URL
- Activity history

## Lawyer (admin verified)
- Private case creation and maintenance
- Tamil Nadu property/civil intake fields
- Per-case document uploads (20 MB per file)
- Case analysis via FastAPI retrieval
- Structured Case Cut report
- Browser print / Save as PDF
- Private case records and activity

## Admin
- User list and role/status changes
- Platform totals, corpus status and recent audit activity
- All API endpoints enforce authentication; admin endpoints check ADMIN role server-side.

## Known MVP boundaries
- Document upload currently stores original files; OCR/automatic document parsing is not yet implemented.
- Analysis uses TF-IDF retrieval over imported full text, not a trained legal model and not an autonomous general-purpose LLM.
- Source excerpt is a retrieval excerpt, not an independently verified ratio decidendi.
- PDF export uses browser Print / Save as PDF rather than a server-side digitally signed PDF.
- Admin bootstrap is manual; public registration cannot self-assign Lawyer or Admin.
- Full production hardening, accessibility audit, external provider terms review and end-to-end testing remain necessary.
