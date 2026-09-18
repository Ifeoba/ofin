"""Step 4 — parse Order Papers into `bill_events` rows.

Per ofin-spec.md §6 step 4: take only text between "ORDERS OF THE DAY" and
"MOTIONS", normalise whitespace (titles wrap across lines), then match the
bill-item pattern. Unmatched bill numbers are expected — the live layer is
newer than the deep layer — and are inserted with no matching `bill_id`.
"""
import io
import re
from datetime import date, datetime
from typing import Optional

import pdfplumber

from common import download_document, get_db_connection, normalize_bill_number
from identify_order_papers import sweep

BILL_ITEM_RE = re.compile(
    r"\d+\.\s*(?P<title>A Bill for an Act.*?)"
    r"\((?P<num>[HS]B\.?\s*\d+)\s*\)\s*"
    r"\((?P<sponsors>.*?)\)\s*[–-]\s*(?P<stage>[A-Z][a-z]+ Reading)",
    re.S,
)

SITTING_RE = re.compile(
    r"(Monday|Tuesday|Wednesday|Thursday|Friday),\s*(\d{1,2}\s+\w+,?\s*20\d\d)"
)
DATE_RE = re.compile(r"(\d{1,2})\s+(\w+),?\s*(20\d\d)")

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11,
    "December": 12,
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def parse_sitting_date(text: str) -> Optional[date]:
    m = SITTING_RE.search(text)
    if not m:
        return None
    dm = DATE_RE.search(m.group(0))
    if not dm:
        return None
    day, month_name, year = dm.groups()
    month = MONTHS.get(month_name.title())
    if not month:
        return None
    return date(int(year), month, int(day))


def extract_agenda_section(full_text: str) -> str:
    upper = full_text.upper()
    start = upper.find("ORDERS OF THE DAY")
    if start == -1:
        return full_text
    end = upper.find("MOTIONS", start)
    return full_text[start:] if end == -1 else full_text[start:end]


def guess_chamber(first_page_text: str) -> str:
    return "House of Representatives" if "HOUSE OF REPRESENTATIVES" in first_page_text.upper() else "Senate"


def parse_order_paper(doc_id: str) -> list:
    pdf_bytes = download_document(doc_id)
    if not pdf_bytes:
        return []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages_text = [p.extract_text() or "" for p in pdf.pages]
    full_text = "\n".join(pages_text)
    first_page = pages_text[0] if pages_text else ""

    chamber = guess_chamber(first_page)
    sitting_date = parse_sitting_date(first_page) or parse_sitting_date(full_text)
    agenda = normalize_whitespace(extract_agenda_section(full_text))

    events = []
    for m in BILL_ITEM_RE.finditer(agenda):
        bill_number = normalize_bill_number(m.group("num"))
        if not bill_number or not sitting_date:
            continue
        events.append(
            {
                "bill_number": bill_number,
                "title": m.group("title").strip(" ,"),
                "sponsors": [s.strip() for s in m.group("sponsors").split(" and ")],
                "stage": m.group("stage").strip(),
                "sitting_date": sitting_date.isoformat(),
                "chamber": chamber,
                "order_paper_id": doc_id,
                "source_url": f"https://nass.gov.ng/documents/download/{doc_id}",
            }
        )
    return events


def run():
    order_paper_ids = sweep()
    conn = get_db_connection()
    cur = conn.cursor()
    total = 0

    for doc_id in order_paper_ids:
        events = parse_order_paper(doc_id)

        # Idempotent re-runs: replace this Order Paper's events rather than
        # duplicating them.
        cur.execute("delete from bill_events where order_paper_id = %s", (doc_id,))

        for e in events:
            cur.execute("select id from bills where bill_number = %s", (e["bill_number"],))
            row = cur.fetchone()
            bill_id = row[0] if row else None

            cur.execute(
                """
                insert into bill_events (bill_id, bill_number, title, chamber, stage,
                                          status, sitting_date, sponsors, order_paper_id,
                                          source_url)
                values (%s, %s, %s, %s, %s, 'scheduled', %s, %s, %s, %s)
                """,
                (
                    bill_id, e["bill_number"], e["title"], e["chamber"], e["stage"],
                    e["sitting_date"], e["sponsors"], e["order_paper_id"], e["source_url"],
                ),
            )
            total += 1
        conn.commit()
        print(f"Order Paper {doc_id}: {len(events)} bill items")

    cur.close()
    conn.close()
    print(f"Done. Inserted {total} bill_events.")


if __name__ == "__main__":
    run()
