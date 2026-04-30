# Local Wikivoyage Snapshots for RAG

1. Open each destination page on Wikivoyage in your browser.
2. Save the page as **Webpage, HTML Only**.
3. Put the `.html` file in `data/knowledge/raw_pages/`.
4. Use lowercase filenames such as `madeira.html`, `kyoto.html`, `dubai.html`.

Filename rule:
- By default, `scripts/build_rag_documents.py` expects the lowercase page title from `wikivoyage_page` (spaces become `_`), for example `new_york_city.html`.
- You can optionally add a `local_html_file` column in `data/knowledge/config/rag_destinations.csv` to override the filename per destination.

Then run:

```bash
PYTHONPATH=. uv run python scripts/build_rag_documents.py
PYTHONPATH=. uv run python scripts/ingest_rag.py
```
