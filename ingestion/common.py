"""Shared helpers for the Òfin ingestion pipeline.

This is a one-off offline pipeline (see ofin-spec.md §6). It runs on your
laptop, writes to Postgres, and never runs again during the demo.
"""
import json
import os
import re
from pathlib import Path
from typing import Optional

import psycopg2
import requests
from dotenv import load_dotenv

# Share the same env file as the Next.js app (project root `.env.local`)
# instead of requiring a second copy under ingestion/.
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")
load_dotenv()  # falls back to ingestion/.env if that's what you're using

DATA_DIR = Path(__file__).resolve().parent / "data"
PDF_DIR = DATA_DIR / "pdfs"
TEXT_DIR = DATA_DIR / "bills"
for d in (DATA_DIR, PDF_DIR, TEXT_DIR):
    d.mkdir(parents=True, exist_ok=True)

NASS_INDEX_URL = "https://nass.gov.ng/documents/bill_track/"
NASS_DOWNLOAD_URL = "https://nass.gov.ng/documents/download/{doc_id}"
USER_AGENT = "Mozilla/5.0"

BILL_NUMBER_RE = re.compile(r"\(?\s*(?P<chamber>HB|SB)\.?\s*(?P<num>\d+)\s*\)?", re.I)

VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-2"  # 1024-dim, matches the `vector(1024)` columns

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


def normalize_bill_number(raw: str) -> Optional[str]:
    """'HB. 2716', 'HB.2716', '(HB 2716)' -> 'HB.2716'."""
    if not raw:
        return None
    m = BILL_NUMBER_RE.search(raw)
    if not m:
        return None
    return f"{m.group('chamber').upper()}.{m.group('num')}"


def download_document(doc_id: str, timeout: int = 60) -> Optional[bytes]:
    """GET a NASS document by id, validated per ofin-spec.md §2.2.

    Many ids return HTTP 200 with 0 bytes — every download must be validated.
    """
    url = NASS_DOWNLOAD_URL.format(doc_id=doc_id)
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    ok = (
        resp.status_code == 200
        and len(resp.content) > 10_000
        and resp.content[:4] == b"%PDF"
    )
    return resp.content if ok else None


def get_db_connection():
    dsn = os.environ["DATABASE_URL"]
    return psycopg2.connect(dsn)


def embed_text(text: str, input_type: str = "document") -> list:
    api_key = os.environ["VOYAGE_API_KEY"]
    resp = requests.post(
        VOYAGE_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"input": text, "model": VOYAGE_MODEL, "input_type": input_type},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def to_pgvector(vec: list) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


def groq_tool_call(
    prompt: str,
    tool_name: str,
    tool_description: str,
    parameters: dict,
    max_tokens: int = 1500,
) -> dict:
    """Ask Groq for a structured response via a forced tool call, instead of
    "return only JSON" text parsing — the response is always well-formed and
    matches `parameters` exactly, the same guarantee the Anthropic tool-use
    calls this replaced were built for.
    """
    api_key = os.environ["GROQ_API_KEY"]
    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_description,
                        "parameters": parameters,
                    },
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": tool_name}},
        },
        timeout=120,
    )
    resp.raise_for_status()
    tool_calls = resp.json()["choices"][0]["message"].get("tool_calls")
    if not tool_calls:
        raise RuntimeError("Groq did not return a tool call")
    return json.loads(tool_calls[0]["function"]["arguments"])
