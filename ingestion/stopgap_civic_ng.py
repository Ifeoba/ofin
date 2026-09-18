"""STOPGAP ONLY — populate `bills` from civic.ng while nass.gov.ng is unreachable.

nass.gov.ng (the spec's actual data source, ofin-spec.md §2) is currently
refusing connections from every network path we tried. civic.ng is up and
lists ~469 bills, but as HTML, not the bill_track JSON endpoint — so this is
a different, deliberately narrower scraper, not a replacement for
pull_index.py / download_bills.py / parse_order_papers.py.

Scope, kept deliberately narrow to respect the trust rules in ofin-spec.md §9:

- Only ingests bills where civic.ng exposes (directly or derivably) a real
  nass.gov.ng document link — never a civic.ng page as the "source_url",
  and never a bill with no NASS reference at all. Most civic.ng list rows
  (~430 of ~469) are bare title/number/chamber with no source link on the
  list page and no detail page either — those are skipped rather than
  given a fabricated or secondary-source link (Rule 7: every page carries
  a permanent link to the *original NASS document*).
- Writes only `bills.{id, bill_number, title, chamber, source_url}`. Never
  touches has_full_text / full_text / summary / topics / embedding — those
  stay false/null until the real pipeline (or a future run of this script
  after nass.gov.ng is back) fetches and extracts the actual PDF text.
  Rule 2 ("no source, no claim") means we do not summarise from a title.
- Writes nothing to `bill_events`. civic.ng's per-bill chip conflates
  reading-stage with terminal status (some bills are tagged literally
  "passed") — exactly what ofin-spec.md Decision 3 / Rule 3 says never to
  render from agenda-derived data. `bill_events.status` also has a
  `check (status <> 'passed')` constraint, so this script doesn't even try.

Once nass.gov.ng is reachable again, run the real pipeline (run_all.py) —
it will update these same rows in place (matching on NASS document id)
with real full text, summaries, and Order Paper events.
"""
import re

from bs4 import BeautifulSoup

from common import USER_AGENT, get_db_connection, normalize_bill_number
import requests

CIVIC_BILLS_URL = "https://civic.ng/bills"
NASS_PDF_RE = re.compile(r"nass\.gov\.ng/documents/billdownload/(\d+)\.pdf", re.I)
NASS_CHIP_RE = re.compile(r"^NASS-(\d+)$", re.I)


def fetch_cards() -> list:
    resp = requests.get(CIVIC_BILLS_URL, headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    return soup.select('div[data-slot="card"]')


def parse_card(card) -> dict | None:
    title_el = card.select_one('div[data-slot="card-title"]')
    if not title_el:
        return None
    title = title_el.get_text(strip=True)

    chips = card.select("div.flex.flex-wrap.gap-2 > div")
    chip_texts = [c.get_text(strip=True) for c in chips]
    if not chip_texts:
        return None
    number_chip = chip_texts[0]
    chamber = chip_texts[1] if len(chip_texts) > 1 else None
    if chamber not in ("Senate", "House of Representatives"):
        return None

    # Prefer a real nass.gov.ng link if civic.ng rendered one on this card.
    nass_id = None
    source_url = None
    ext_link = card.select_one('a[href*="nass.gov.ng"]')
    if ext_link and ext_link.get("href"):
        m = NASS_PDF_RE.search(ext_link["href"])
        if m:
            nass_id = m.group(1)
            source_url = ext_link["href"]

    # Otherwise, civic.ng sometimes labels the bill with the NASS document id
    # directly (e.g. "NASS-11208") when no HB/SB number is known yet. That id
    # follows the same download pattern documented in ofin-spec.md §2.2.
    if not nass_id:
        m = NASS_CHIP_RE.match(number_chip)
        if m:
            nass_id = m.group(1)
            source_url = f"https://nass.gov.ng/documents/download/{nass_id}"

    if not nass_id:
        return None  # no real NASS document reference — skip, per Rule 7

    bill_number = normalize_bill_number(number_chip)  # None for "NASS-xxxxx"

    return {
        "id": nass_id,
        "bill_number": bill_number,
        "title": title,
        "chamber": chamber,
        "source_url": source_url,
    }


def run():
    cards = fetch_cards()
    print(f"{len(cards)} bill cards on civic.ng/bills")

    conn = get_db_connection()
    cur = conn.cursor()
    saved, skipped = 0, 0

    for card in cards:
        row = parse_card(card)
        if not row:
            skipped += 1
            continue

        cur.execute(
            """
            insert into bills (id, bill_number, title, chamber, source_url)
            values (%(id)s, %(bill_number)s, %(title)s, %(chamber)s, %(source_url)s)
            on conflict (id) do update set
                bill_number = excluded.bill_number,
                title = excluded.title,
                chamber = excluded.chamber,
                source_url = excluded.source_url
            """,
            row,
        )
        saved += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Done. Upserted {saved} bills with a real NASS reference, skipped {skipped}.")


if __name__ == "__main__":
    run()
