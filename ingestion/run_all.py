"""One-off ingestion pipeline (ofin-spec.md §4/§6).

Run this on your laptop after applying db/schema.sql and setting
DATABASE_URL / GROQ_API_KEY / VOYAGE_API_KEY. It never runs again during
the demo — nothing at demo time depends on nass.gov.ng being up.

Usage: python run_all.py
"""
import chunk_embed
import download_bills
import identify_order_papers
import parse_order_papers
import pull_index
import summarize


def main():
    print("== Step 1: pull index ==")
    pull_index.pull_index(force=True)

    print("== Step 2: identify Order Papers ==")
    identify_order_papers.sweep(force=True)

    print("== Step 3: download + extract bills ==")
    download_bills.run()

    print("== Step 4: parse Order Papers -> bill_events ==")
    parse_order_papers.run()

    print("== Step 5: summarise bills (Groq) ==")
    summarize.run()

    print("== Step 6: chunk + embed ==")
    chunk_embed.run()

    print("Done.")


if __name__ == "__main__":
    main()
