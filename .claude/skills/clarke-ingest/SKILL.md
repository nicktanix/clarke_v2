---
name: clarke-ingest
description: "Ingest documents and files into CLARKE. Use when: 'ingest this file', 'add to clarke', 'import document', 'feed this to clarke'"
---

# CLARKE Content Ingestion

## When to Use
- "ingest this file into clarke"
- "add this document to CLARKE's knowledge"
- "import our runbooks"
- "feed the README to clarke"
- "index this directory"

## Workflow

### Single File

1. Read the file using the Read tool
2. Determine content_type from extension:
   - `.md` -> `text/markdown`
   - `.py`, `.js`, `.ts`, `.go`, `.rs` -> `text/plain`
   - `.html` -> `text/html`
   - `.json` -> `application/json`
   - `.pdf` -> `application/pdf`
3. Call `clarke_ingest_document` with the file content
4. Show result: document_id, status

### Directory

1. Use Glob to find files matching a pattern (e.g., `docs/**/*.md`)
2. For each file, read and ingest
3. Show progress and results table

### After Ingestion

Suggest verification: "Use `/clarke-recall` to test if the content is retrievable. Try asking about something from the ingested document."

## Tools

| Tool | Purpose |
|------|---------|
| `clarke_ingest_document` | Ingest a document into CLARKE |

## Checklist
- [ ] Read the source file(s)
- [ ] Determine content type
- [ ] Call `clarke_ingest_document` for each
- [ ] Verify ingestion status
- [ ] Test retrieval with `/clarke-recall`

## Example

**User says:** "ingest the docs/ directory"

**Agent does:**
1. Globs `docs/**/*.md` -> finds 5 files
2. Reads each, ingests with content_type=text/markdown
3. Shows results:
```
Ingestion Results
| File                    | Doc ID        | Status    |
|-------------------------|---------------|-----------|
| docs/clarke.md          | doc_01HX...   | completed |
| docs/draft/spec-v3.1.md | doc_01HY...   | completed |
| ...                     | ...           | ...       |

5/5 files ingested successfully.
```
4. Suggests: "Try `/clarke-recall` with 'what is the trust ordering' to verify"
