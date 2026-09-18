"""Step 5 — pre-generate summaries (ofin-spec.md §7.1), one Groq call per
bill, written once to the `bills` row.

Uses a forced tool call instead of "return only JSON" text parsing so the
response is always well-formed, matching the schema exactly.
"""
import json

from common import get_db_connection, groq_tool_call

SUMMARIZE_PARAMETERS = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "why_introduced": {"type": "string"},
        "what_changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "change": {"type": "string"},
                    "clause_ref": {"type": "string"},
                    "page": {"type": "integer"},
                },
                "required": ["change", "clause_ref"],
            },
        },
        "who_affected": {"type": "array", "items": {"type": "string"}},
        "topics": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "why_introduced", "what_changes", "who_affected", "topics"],
}

PROMPT = """You are explaining Nigerian legislation to an ordinary citizen with no legal training.

Below is the full text of a bill before the National Assembly.

Rules:
- Every entry in what_changes MUST cite a clause or page from the text below. If you cannot cite it, leave it out.
- No speculation about political motives, sponsors, or likelihood of passage.
- If the text is too fragmentary to summarise, set summary to "Source document could not be reliably read." and return empty arrays.
- Nigerian English. No legalese. Write for a secondary-school reading level.
- summary: one paragraph, max 80 words.
- why_introduced: max 50 words, based only on the bill's stated objectives.
- topics: 2-5 lowercase tags from: education, health, tax, electricity, children, security, agriculture, technology, finance, transport, environment, justice, employment, housing, gender.

BILL TITLE: {title}
FULL TEXT:
{text}
"""


def summarize_bill(title: str, text: str) -> dict:
    return groq_tool_call(
        prompt=PROMPT.format(title=title, text=text[:180_000]),
        tool_name="summarize_bill",
        tool_description="Structured plain-language summary of a Nigerian bill for citizens.",
        parameters=SUMMARIZE_PARAMETERS,
    )


def run():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "select id, title, full_text from bills where has_full_text = true and summary is null"
    )
    rows = cur.fetchall()
    print(f"{len(rows)} bills to summarise")

    for i, (bill_id, title, full_text) in enumerate(rows, 1):
        try:
            result = summarize_bill(title, full_text)
        except Exception as exc:
            print(f"[{i}/{len(rows)}] {bill_id} FAILED: {exc}")
            continue

        cur.execute(
            """
            update bills set
                summary = %s, why_introduced = %s, what_changes = %s,
                who_affected = %s, topics = %s
            where id = %s
            """,
            (
                result["summary"],
                result["why_introduced"],
                json.dumps(result["what_changes"]),
                result["who_affected"],
                result["topics"],
                bill_id,
            ),
        )
        conn.commit()
        print(f"[{i}/{len(rows)}] {bill_id} summarised")

    cur.close()
    conn.close()


if __name__ == "__main__":
    run()
