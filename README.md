# Òfin

**Understand what Nigeria's National Assembly is actually doing.**

Search any issue. Find the bills behind it. Get a plain-language explanation.
See exactly where the bill is — and verify every sentence against the original document.

Full build spec: [ofin-spec.md](./ofin-spec.md).

## Data recon (verified against the live site)

- `GET https://nass.gov.ng/documents/bill_track/?draw=1&start=0&length=3000` returns all
  2,660 bill-tracker rows as JSON. The `search[value]` param is ignored — pull once, filter
  locally.
- `GET https://nass.gov.ng/documents/download/{id}` returns the PDF. Many ids return HTTP 200
  with 0 bytes — every download must be validated (`status 200`, `len > 10_000`, starts with
  `%PDF`).
- Status fields (first/second/committee/third reading) are almost entirely empty and the
  tracker itself is stale (2000–2021, plus 0-byte "Progression Chart" placeholders for
  2024–2026). A status stepper built from this data would be blank.
- Current activity instead lives in **Order Papers** — document ids in the 11200s range,
  confirmed working for Nov 2025 and Apr 2026 sittings. They cleanly expose title, bill
  number, sponsors, and stage under `ORDERS OF THE DAY`.
- Consequence: two layers that barely overlap —

  | Layer | Source | Coverage | Gives you |
  |---|---|---|---|
  | Live | Order Papers | 2025–2026 | What's moving now, stage, sponsors |
  | Deep | Bill PDFs | 2016–2021 | Full text → explanations with clause citations |

  The UI says so rather than hiding it (see the footer on every page).
- **nass.gov.ng is currently unreachable** (connection refused from every network path we
  tried, not a 404/500 — the site itself appears down). Real data for local dev is coming
  from a stopgap scraper against [civic.ng](https://civic.ng) instead — see
  `ingestion/stopgap_civic_ng.py` for exactly what it does and does not pull, and why. Once
  nass.gov.ng is back, `run_all.py` is the canonical pipeline and updates the same rows in
  place (matched on NASS document id).

## Trust rules

- Every AI sentence traces to a clause, page, or source document. No source, no claim —
  ask-a-bill returns exactly `"This bill does not address that."` when the extracts don't
  answer the question.
- Order Paper items are labelled **"Listed for {stage}"**, never "passed" or "approved".
  `bill_events.status` has a database-level `check (status <> 'passed')`.
- No sentiment, controversy scoring, or sponsor evaluation.

## Architecture

```
Ingestion (Python, run once) ──▶ Postgres + pgvector ◀── Next.js app
                                                              │
                                                          Groq API
                                                     (ask-a-bill, runtime)
```

LLM calls (summarisation + ask-a-bill) run on Groq rather than Claude — both use forced
tool calls, so the "no source, no claim" structured-output guarantee is unaffected. See
`lib/groq.ts` / `ingestion/common.py`'s `groq_tool_call`.

Ingestion is a one-off offline script — it runs on your laptop and never runs again during
the demo. Nothing at demo time depends on nass.gov.ng being up.

Database is Postgres with the `vector` extension — [Neon](https://neon.tech) is the
recommended host: free tier, native pgvector, and built for serverless/Vercel deployments
(unlike PocketBase or a self-managed Postgres box, it needs no persistent server of its own
to keep running).

## Setup

1. **Database.** Create a Neon project (or any Postgres with the `vector` extension —
   Supabase also works), copy `.env.example` to `.env.local`, and set `DATABASE_URL`.

   ```
   npm run db:schema
   npm run db:seed:mock   # optional — a few placeholder rows so the UI isn't empty
   ```

2. **API keys.** Set `GROQ_API_KEY` (ask-a-bill + summarisation) and, optionally,
   `VOYAGE_API_KEY` (semantic search + retrieval; without it, search falls back to a plain
   text match and ask-a-bill falls back to reading a bill's chunks in order).

3. **App.**

   ```
   npm install
   npm run dev
   ```

4. **Ingestion** (populates real data — see `ingestion/`):

   ```
   cd ingestion
   python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
   ./venv/bin/python run_all.py
   ```

   This pulls the bill-tracker index, identifies Order Papers, downloads and extracts ~200
   bill PDFs, parses Order Papers into `bill_events`, summarises bills with Groq, and
   chunks + embeds full text. It's idempotent — re-running it updates rows in place rather
   than duplicating them. (Currently blocked on nass.gov.ng being down — see above. In the
   meantime, `./venv/bin/python stopgap_civic_ng.py` populates real bill metadata from
   civic.ng.)

## Screens

Four, per the spec: Home (search + topic chips + this week's activity), Results (semantic
search over bills), Bill page (summary, what-changes with clause citations, timeline,
ask-a-bill), Activity (reverse-chronological Order Paper events).

## Out of scope

Notifications, follow-a-topic, daily digest, full Senate + House coverage, Votes &
Proceedings parsing, user accounts, state assemblies, sentiment/controversy scoring.

## Known limitations

- Corpus is a subset by design (~200 bills, ~20 Order Papers) — see the recon table above.
- Bill PDFs are assumed to be text-layer, not scans; anything under 500 characters of
  extracted text is discarded rather than OCR'd.
