"""Step 2 — identify Order Papers by sweeping the 11100-11260 id range.

Order Papers are not reliably labelled in the bill-tracker index (see
ofin-spec.md §2.4 / §6 step 2). We download each id in the range and check
page 1 for the literal string "ORDER PAPER".
"""
import io
import json
import re

import pdfplumber

from common import DATA_DIR, PDF_DIR, download_document

ORDER_PAPER_RE = re.compile(r"ORDER PAPER", re.I)
RANGE_START = 11100
RANGE_END = 11260
CACHE = DATA_DIR / "order_paper_ids.json"


def sweep(force: bool = False) -> list:
    if CACHE.exists() and not force:
        return json.loads(CACHE.read_text())

    found = []
    for doc_id in range(RANGE_START, RANGE_END + 1):
        content = download_document(str(doc_id))
        if not content:
            continue
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                first_page_text = pdf.pages[0].extract_text() or ""
        except Exception:
            continue
        if ORDER_PAPER_RE.search(first_page_text):
            found.append(str(doc_id))
            (PDF_DIR / f"{doc_id}.pdf").write_bytes(content)
            print(f"Order Paper: {doc_id}")

    CACHE.write_text(json.dumps(found))
    print(f"Found {len(found)} Order Papers -> {CACHE}")
    return found


if __name__ == "__main__":
    sweep(force=True)
