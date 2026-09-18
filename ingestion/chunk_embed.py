"""Step 6 — chunk full text (~1,000 tokens, 150 overlap, approximated by
characters) and embed chunks + bill title/summary (ofin-spec.md §6 step 6).
"""
import re

from common import embed_text, get_db_connection, to_pgvector

CHUNK_CHARS = 4000
OVERLAP_CHARS = 600
SECTION_RE = re.compile(r"Section\s+(\d+[A-Za-z]?)")


def chunk_text(text: str) -> list:
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + CHUNK_CHARS, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = end - OVERLAP_CHARS
    return chunks


def detect_clause_ref(chunk: str):
    m = SECTION_RE.search(chunk)
    return f"Section {m.group(1)}" if m else None


def run():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "select id, title, summary, full_text, page_count from bills "
        "where has_full_text = true and full_text is not null"
    )
    rows = cur.fetchall()
    print(f"{len(rows)} bills to chunk + embed")

    for i, (bill_id, title, summary, full_text, page_count) in enumerate(rows, 1):
        cur.execute("delete from bill_chunks where bill_id = %s", (bill_id,))

        chunks = chunk_text(full_text)
        chars_per_page = max(1, len(full_text) // max(1, page_count or 1))

        for idx, chunk in enumerate(chunks):
            offset = idx * (CHUNK_CHARS - OVERLAP_CHARS)
            page_number = min(page_count or 1, offset // chars_per_page + 1)
            clause_ref = detect_clause_ref(chunk)
            vec = embed_text(chunk, input_type="document")
            cur.execute(
                """
                insert into bill_chunks (bill_id, chunk_index, content, page_number,
                                          clause_ref, embedding)
                values (%s, %s, %s, %s, %s, %s::vector)
                """,
                (bill_id, idx, chunk, page_number, clause_ref, to_pgvector(vec)),
            )

        title_summary = f"{title}\n\n{summary or ''}"
        bill_vec = embed_text(title_summary, input_type="document")
        cur.execute(
            "update bills set embedding = %s::vector where id = %s",
            (to_pgvector(bill_vec), bill_id),
        )

        conn.commit()
        print(f"[{i}/{len(rows)}] {bill_id}: {len(chunks)} chunks")

    cur.close()
    conn.close()


if __name__ == "__main__":
    run()
