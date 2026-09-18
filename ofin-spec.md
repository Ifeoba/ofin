# Òfin — Build Spec

**Understand what Nigeria's National Assembly is actually doing.**

Search any issue. Find the bills behind it. Get a plain-language explanation.
See exactly where the bill is — and verify every sentence against the original document.

- **Owner:** Ifeoluwa
- **Deadline:** Monday 21 September 2026 (4 working days)
- **Status:** scope locked, ready to build

---

## 1. The problem

Nigeria's National Assembly publishes a lot. Almost none of it is legible to a citizen.

The information exists as parliamentary artefacts — bill tracker rows, Order Papers, Votes &
Proceedings, Hansard — written in procedural language, for people already inside the process.

A normal person doesn't ask *"show me SB.1023."* They ask:

- "Are there any new laws about school fees?"
- "What is government doing about electricity?"
- "Has anything changed about taxation for small businesses?"

Nothing translates those questions into legislation.

### The gap is confirmed, not assumed

`civic.ng` is the strongest existing civic tracker in this space. It tracks **464 bills**, with
sponsors and source URLs. Its own bill records display:

> *"Summary unavailable in the current source record."*

It tracks. It does not explain. **Understanding is the missing layer.**

Òfin is not another tracker. It is a citizen-facing understanding layer on top of government records.

---

## 2. Data reconnaissance — already done

This is verified against the live site, not assumed. It is also a credible chunk of the submission:
most entries will be scraping blind.

### 2.1 Working endpoint — the bill corpus

```
GET https://nass.gov.ng/documents/bill_track/?draw=1&start=0&length=3000
```

Returns JSON. **2,660 records.** Row shape:

```json
["HB. 1602 National Minimum Wage Bill, 2019 (HB. 1602 ) ",
 "House of Representatives", "2021-11-16", "2021-11-30 00:00:00", null, null, "10235"]
```

| Index | Field |
|---|---|
| 0 | Title (bill number embedded in the string) |
| 1 | Chamber — 1,770 Senate / 890 House |
| 2 | First reading date |
| 3 | Second reading date |
| 4 | Committee date |
| 5 | Third reading date |
| 6 | Document ID |

The `search[value]` parameter **is ignored** — the server returns all 2,660 rows regardless.
Pull once, filter locally.

### 2.2 Document download

```
GET https://nass.gov.ng/documents/download/{id}
```

Returns `application/pdf`. Confirmed working: id `10235` → 456 KB, id `11220` → 11 pages.

**Many ids return HTTP 200 with 0 bytes.** Every download must be validated before storage:

```python
ok = resp.status_code == 200 and len(resp.content) > 10_000 and resp.content[:4] == b"%PDF"
```

### 2.3 Two dead ends — do not spend time here

**Status fields are almost entirely empty.** Across all 2,660 rows:

| Stage | Populated |
|---|---|
| First reading | 428 |
| Second reading | 35 |
| Committee | **0** |
| Third reading | **1** |

A status stepper driven by this data would be blank. Status must come from Order Papers instead.

**The bill tracker is stale.** Bills run 2000–2021 and stop. The only 2024–2026 entries are
"Bills Progression Chart" documents — and **every one of them returns 0 bytes.** The 10th
Assembly's ~1,033 bills are not individually retrievable from the tracker.

### 2.4 Where current activity actually lives — Order Papers

Document ids in the 11200s are 10th Assembly Order Papers (confirmed: Nov 2025, Apr 2026).
They parse cleanly and they are highly structured:

```
ORDERS OF THE DAY
BILLS
1. A Bill for an Act to Establish the Department of State Services Research and
   Development in the Department of State Services and for Related Matters
   (HB.2716) (Hon. Abbas Tajudeen and Hon. Austin Asama) – Second Reading.
2. A Bill for an Act to Establish the National Institute for Public Health and
   Infectious Diseases ... (HB. 2629) (Hon. Abbas Tajudeen and Hon. Amobi Ogah
   Godwin) – Second Reading.
```

Every field needed is present: **title, bill number, sponsors, stage** — and the sitting date
sits in the page header (`Thursday, 23 April, 2026`).

**This is the live feed.**

### 2.5 The two-layer consequence

| Layer | Source | Coverage | Gives you |
|---|---|---|---|
| **Live** | Order Papers | 2025–2026 | What's moving now, stage, sponsors |
| **Deep** | Bill PDFs | 2016–2021 | Full text → explanations with clause citations |

They barely overlap. Say so in the UI rather than hiding it.

---

## 3. Locked decisions

| # | Decision | Chosen |
|---|---|---|
| 1 | Name | **Òfin** (Yoruba: *law*) |
| 2 | Scope | Both layers — live activity **and** deep understanding |
| 3 | Scheduled vs confirmed | Order Papers only, labelled **"Listed for"**, never "passed" |
| 4 | Ingest volume | ~20 Order Papers + ~200 full bills |
| 5 | Summaries | **Pre-generated at ingest** and stored |
| 6 | Ask box | **Single bill only** |
| 7 | Stack | Next.js + Claude API + Postgres/pgvector on Vercel |

### Decision 3 is the trust spine

An Order Paper is the day's **agenda**, not the outcome. A bill "listed for Second Reading"
may have been stood down, deferred or never reached.

**Rendering an agenda item as a result would be the exact misinformation Òfin exists to fix.**

So the live feed says:

> **Listed for Second Reading** — House of Representatives, 23 April 2026
> *Order Papers record scheduled business, not outcomes. Confirmation appears in Votes &
> Proceedings.* [View the Order Paper]

This is a feature. Lead with it in the demo.

### Explicitly out of scope

Notifications · follow-a-topic · daily digest · Senate **and** House full coverage ·
Votes & Proceedings parsing · user accounts · state assemblies · sentiment or "what's controversial"

---

## 4. Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Ingestion   │────▶│   Postgres   │◀────│   Next.js    │
│  (Python,    │     │  + pgvector  │     │   app        │
│   run once)  │     └──────────────┘     └──────┬───────┘
└──────┬───────┘                                 │
       │                                         ▼
       ▼                                  ┌──────────────┐
  Claude API                              │  Claude API  │
  (batch summaries,                       │  (ask-a-bill,│
   written once)                          │   live)      │
```

Ingestion is a **one-off offline script**, not a live service. It runs on your laptop,
writes to Postgres, and never runs again during the demo. Nothing at demo time depends on
nass.gov.ng being up.

---

## 5. Data model

```sql
create extension if not exists vector;

create table bills (
  id              text primary key,        -- NASS document id, e.g. '10235'
  bill_number     text,                    -- 'HB.2716' / 'SB.851'
  title           text not null,
  chamber         text not null,           -- 'Senate' | 'House of Representatives'
  source_url      text not null,           -- canonical NASS download link
  has_full_text   boolean default false,
  full_text       text,
  page_count      int,
  -- AI layer, pre-generated
  summary         text,                    -- 1 paragraph, plain language
  why_introduced  text,
  what_changes    jsonb,                   -- [{change, clause_ref, page}]
  who_affected    text[],                  -- ['parents','schools','state governments']
  topics          text[],                  -- ['education','children']
  embedding       vector(1024),
  created_at      timestamptz default now()
);

-- one row per bill mention in one Order Paper
create table bill_events (
  id              bigserial primary key,
  bill_id         text references bills(id),
  bill_number     text not null,           -- match key; bill may not be in `bills`
  title           text not null,
  chamber         text not null,
  stage           text not null,           -- 'First Reading' | 'Second Reading' | ...
  status          text not null default 'scheduled',  -- never 'passed'
  sitting_date    date not null,
  sponsors        text[],
  order_paper_id  text not null,
  source_url      text not null
);

create table bill_chunks (
  id          bigserial primary key,
  bill_id     text references bills(id),
  chunk_index int,
  content     text,
  page_number int,
  clause_ref  text,                        -- 'Section 14' where detectable
  embedding   vector(1024)
);

create index on bills using ivfflat (embedding vector_cosine_ops);
create index on bill_chunks using ivfflat (embedding vector_cosine_ops);
create index on bill_events (sitting_date desc);
```

`status` defaults to `'scheduled'` and there is **no code path that writes `'passed'`**.
Enforce it at the database level if you have five spare minutes.

---

## 6. Ingestion pipeline

### Step 1 — Pull the index

```python
r = requests.get("https://nass.gov.ng/documents/bill_track/",
                 params={"draw": 1, "start": 0, "length": 3000},
                 headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
rows = r.json()["data"]   # 2,660
```

### Step 2 — Split the corpus

```python
import re
CHART = re.compile(r"PROGRESSION CHART", re.I)
ORDER = re.compile(r"ORDER PAPER|VOTES AND PROCEEDINGS", re.I)

charts = [r for r in rows if CHART.search(r[0])]          # skip: all 0 bytes
bills  = [r for r in rows if not CHART.search(r[0])]
```

Order Papers are not reliably labelled in the index. Identify them by **downloading ids in the
11100–11260 range and reading page 1** for `ORDER PAPER`. Cheap and deterministic.

### Step 3 — Select ~200 bills

Prioritise, in order:
1. Has a populated first-reading date (428 candidates)
2. Title matches a demo topic — education, health, tax, electricity, children, technology
3. Most recent first

Download, validate (§2.2), extract with `pdfplumber`, discard anything under 500 characters
of text (scanned image, no OCR budget).

### Step 4 — Parse Order Papers

```python
BILL_ITEM = re.compile(
    r"^\s*\d+\.\s*(?P<title>A Bill for an Act.*?)"
    r"\((?P<num>[HS]B\.?\s*\d+)\s*\)\s*"
    r"\((?P<sponsors>.*?)\)\s*[–-]\s*(?P<stage>[A-Z][a-z]+ Reading)",
    re.S | re.M)

SITTING = re.compile(r"(Monday|Tuesday|Wednesday|Thursday|Friday),\s*(\d{1,2}\s+\w+,\s*20\d\d)")
```

Take only text after `ORDERS OF THE DAY` and before `MOTIONS`. Normalise whitespace first —
titles wrap across lines. Normalise bill numbers (`HB. 2716`, `HB.2716` → `HB.2716`) before matching
against `bills`.

Unmatched bill numbers are **fine and expected** — the live layer is newer than the deep layer.
Show the event with title and source link, and no explanation. Don't drop it.

### Step 5 — Pre-generate summaries

One Claude call per bill, results written to the `bills` row. ~200 calls, batched, run overnight.

### Step 6 — Chunk and embed

Chunk full text ~1,000 tokens with 150 overlap. Capture page number and, where a
`Section \d+` heading is detectable, `clause_ref`. Embed chunks and bill titles+summaries.

---

## 7. Prompts

### 7.1 Summarisation (ingest-time, run once per bill)

```
You are explaining Nigerian legislation to an ordinary citizen with no legal training.

Below is the full text of a bill before the National Assembly.

Return ONLY valid JSON, no markdown fences, no preamble:

{
  "summary": "One paragraph, max 80 words. What this bill is, in everyday language.",
  "why_introduced": "Max 50 words, based only on the bill's stated objectives.",
  "what_changes": [
    {"change": "plain-language description",
     "clause_ref": "Section 14",
     "page": 3}
  ],
  "who_affected": ["short noun phrases"],
  "topics": ["2-5 lowercase tags from: education, health, tax, electricity,
              children, security, agriculture, technology, finance, transport,
              environment, justice, employment, housing, gender"]
}

Rules:
- Every entry in what_changes MUST cite a clause or page from the text below.
  If you cannot cite it, leave it out.
- No speculation about political motives, sponsors, or likelihood of passage.
- If the text is too fragmentary to summarise, set summary to
  "Source document could not be reliably read." and return empty arrays.
- Nigerian English. No legalese. Write for a secondary-school reading level.

BILL TITLE: {title}
FULL TEXT:
{text}
```

### 7.2 Ask-a-bill (runtime, single bill, grounded)

```
Answer the user's question using ONLY the bill extracts below.

Return ONLY valid JSON:
{
  "answer": "Plain language. 2-4 sentences.",
  "citations": [{"clause_ref": "Section 14", "page": 3, "quote": "exact quote"}],
  "grounded": true
}

Hard rules:
- If the extracts do not answer the question, set "grounded": false and make
  "answer" exactly: "This bill does not address that."
  Do not guess. Do not use outside knowledge of Nigerian law.
- Every factual claim in "answer" must have a matching citation.
- If the answer is partial, say what the bill DOES cover and what it does not.
- Never state whether the bill is law. Never predict whether it will pass.

BILL: {title} ({bill_number})
EXTRACTS:
{chunks}

QUESTION: {question}
```

The frontend must render `grounded: false` differently — muted, no citation chips.
**A visible, confident "This bill does not address that" is the single most persuasive
thing in the demo.**

---

## 8. Screens

Four. No more.

### 8.1 Home
Large search box: *"What do you want to understand?"*
Under it, six one-tap topic chips: `education` `health` `tax` `electricity` `children` `security`
Below: **This week in the National Assembly** — last 5 `bill_events`, each labelled
*Listed for {stage} · {date}*.

### 8.2 Results
Query → embed → cosine search over `bills.embedding`, top 12.
Each card: title · bill number · chamber · topic tags · one-line summary ·
`Full text available` or `Listed only` badge.

### 8.3 Bill page
- Title, bill number, chamber, sponsors
- **What is this?** — `summary`
- **Why was it introduced?** — `why_introduced`
- **What would change?** — `what_changes`, each with a `[Section 14 ▸]` chip that opens the
  exact extract
- **Who could this affect?** — chips
- **Where is it?** — timeline from `bill_events`, every node labelled *Listed for*, with
  the standing caveat and a link to the Order Paper
- **Read the original** — direct NASS PDF link
- **Ask about this bill** — the §7.2 box

### 8.4 Activity
Reverse-chronological `bill_events`. Filter by chamber. Each row links to its Order Paper.

---

## 9. Trust rules — non-negotiable

1. Every AI sentence traces to a clause, page or source document.
2. No source ⇒ no claim. `"This bill does not address that."`
3. Order Paper items are **"Listed for"**, never "passed", never "approved".
4. The word *law* appears only where presidential assent is evidenced. Nothing in this corpus
   is evidenced that way, so it never appears.
5. Corpus limits are stated on the page, not buried: *"Full-text explanations cover bills from
   2016–2021. Activity covers 2025–2026."*
6. No sentiment, no controversy scoring, no partisan framing, no sponsor evaluation.
7. Every page carries a permanent link to the original NASS document.

Rule 2 and rule 3 are what separate Òfin from an LLM confidently summarising a PDF.

---

## 10. Four-day plan

### Thursday 17 — data
- [ ] Postgres up (Neon or Supabase), schema applied
- [ ] Pull and cache the 2,660-row index
- [ ] Download + validate ~200 bill PDFs, extract text
- [ ] Sweep ids 11100–11260, identify ~20 Order Papers
- [ ] **Gate:** ≥150 bills with real text, ≥15 Order Papers parsed

### Friday 18 — AI layer
- [ ] Order Paper parser → `bill_events`, bill-number normalisation, matching
- [ ] Batch summarisation (§7.1) across all bills
- [ ] Chunk + embed; embed bill titles/summaries
- [ ] **Gate:** searching `child education` in psql returns sensible bills

### Saturday 19 — app
- [ ] Next.js scaffold, search endpoint, results page
- [ ] Bill page with citation chips
- [ ] Activity feed
- [ ] Ask-a-bill endpoint, grounded/ungrounded states
- [ ] **Gate:** full click-through works locally

### Sunday 20 — polish
- [ ] Visual pass, mobile layout, loading states, empty states
- [ ] Deploy to Vercel
- [ ] Verify 3 demo topics end-to-end on production
- [ ] Record demo video
- [ ] **Gate:** live URL a stranger can use

### Monday 21 — submit
- [ ] README with §2 recon findings included
- [ ] Buffer. Build nothing new.

**If you slip:** cut the Activity page first (§8.4), then reduce to 100 bills. Never cut the
citation chips — they are the product.

---

## 11. Demo script — 3 minutes

1. **The problem.** 1,033 bills before the 10th Assembly. Ask anyone in this room to name one.
2. **Type `child education`.** Real bills, ranked by meaning, not keyword.
3. **Open one.** Plain-language explanation. Click `[Section 14 ▸]` — the exact clause appears.
   *"Every sentence here is checkable."*
4. **Ask it something it can't answer.** It says **"This bill does not address that."**
   *"It refuses to guess. That's the whole design."*
5. **The activity feed.** *"Listed for Second Reading, 23 April 2026 — pulled from the actual
   House Order Paper. Note it says listed, not passed. Order Papers are agendas, not outcomes.
   Getting that distinction wrong is how civic misinformation starts."*
6. **Close.** *"The National Assembly publishes everything. Almost none of it is readable.
   Òfin is the understanding layer."*

Step 4 is the winning moment. Practise it. Have the question that fails ready in advance.

---

## 12. Assumptions to correct

These were not settled and are assumed. Flag anything wrong.

- Solo build, you are writing the code
- Submission is a live URL + repo + video
- Claude API budget covers ~200 summarisation calls
- `ofin.ng` unchecked — Vercel subdomain is acceptable for submission
- Bill PDFs are text-layer, not scans. Spot-check 10 early; if many are scanned, raise the
  bill count and drop the ones that fail, rather than adding OCR

---

## 13. One-line pitch

> **Òfin — understand what Nigeria's government is actually doing.**
> Search any issue. Find the bills. Read them in plain language. Verify every line against
> the original document.
