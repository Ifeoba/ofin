"""Step 3 — select and download ~200 bills, per the priority order in
ofin-spec.md §6 step 3:

  1. Has a populated first-reading date
  2. Title matches a demo topic (education, health, tax, electricity,
     children, technology)
  3. Most recent first

Every PDF is validated before storage, and anything yielding under 500
characters of text is discarded (scanned image, no OCR budget).
"""
import io
import re

import pdfplumber

from common import PDF_DIR, TEXT_DIR, download_document, get_db_connection, normalize_bill_number
from pull_index import pull_index

CHART_RE = re.compile(r"PROGRESSION CHART", re.I)
DEMO_TOPICS_RE = re.compile(r"education|health|tax|electricity|child|technology", re.I)
TARGET_COUNT = 200
MIN_TEXT_LEN = 500


def split_corpus(rows):
    charts = [r for r in rows if CHART_RE.search(r[0])]
    bills = [r for r in rows if not CHART_RE.search(r[0])]
    return bills, charts


def prioritize(bills):
    def sort_key(row):
        has_first_reading = 1 if row[2] else 0
        topic_match = 1 if DEMO_TOPICS_RE.search(row[0]) else 0
        return (has_first_reading, topic_match, row[2] or "")

    return sorted(bills, key=sort_key, reverse=True)


def extract_pages(pdf_bytes: bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def run(limit: int = TARGET_COUNT):
    rows = pull_index()
    bills, _charts = split_corpus(rows)
    ordered = prioritize(bills)

    conn = get_db_connection()
    cur = conn.cursor()
    saved = 0

    for row in ordered:
        if saved >= limit:
            break

        title_raw, chamber, _first_reading, *_rest, doc_id = row
        bill_number = normalize_bill_number(title_raw)
        if not bill_number:
            continue

        pdf_bytes = download_document(doc_id)
        if not pdf_bytes:
            continue

        pages = extract_pages(pdf_bytes)
        full_text = "\n\n".join(pages).strip()
        if len(full_text) < MIN_TEXT_LEN:
            continue

        (PDF_DIR / f"{doc_id}.pdf").write_bytes(pdf_bytes)
        (TEXT_DIR / f"{doc_id}.txt").write_text(full_text)

        title = re.sub(r"\s*\(\s*[HS]B\.?\s*\d+\s*\)\s*$", "", title_raw).strip()

        cur.execute(
            """
            insert into bills (id, bill_number, title, chamber, source_url,
                                has_full_text, full_text, page_count)
            values (%s, %s, %s, %s, %s, true, %s, %s)
            on conflict (id) do update set
                bill_number = excluded.bill_number,
                title = excluded.title,
                chamber = excluded.chamber,
                source_url = excluded.source_url,
                has_full_text = true,
                full_text = excluded.full_text,
                page_count = excluded.page_count
            """,
            (
                doc_id,
                bill_number,
                title,
                chamber,
                f"https://nass.gov.ng/documents/download/{doc_id}",
                full_text,
                len(pages),
            ),
        )
        conn.commit()
        saved += 1
        print(f"[{saved}/{limit}] {bill_number} {title[:60]}")

    cur.close()
    conn.close()
    print(f"Done. Saved {saved} bills with full text.")


if __name__ == "__main__":
    run()
