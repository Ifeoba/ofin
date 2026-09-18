-- Mock/dev seed data — NOT real ingestion output.
-- Lets the app render something before you run the ingestion pipeline.
-- Replace with real data by running: python ingestion/run_all.py

insert into bills (id, bill_number, title, chamber, source_url, has_full_text,
                    full_text, page_count, summary, why_introduced, what_changes,
                    who_affected, topics)
values (
  'mock-1',
  'SB.9001',
  '[DEV SEED] A Bill for an Act to Improve Access to Basic Education',
  'Senate',
  'https://nass.gov.ng/documents/download/10235',
  true,
  'Section 1. This is placeholder extract text for local development only. Run the ingestion pipeline to load real bill text. Section 14. Placeholder clause text for citation testing.',
  1,
  '[DEV SEED] Mock summary for local development — replace by running ingestion/summarize.py once ANTHROPIC_API_KEY is set.',
  '[DEV SEED] Mock rationale — not from a real bill.',
  '[{"change": "[DEV SEED] Placeholder change for UI testing", "clause_ref": "Section 14", "page": 1}]'::jsonb,
  array['parents', 'schools'],
  array['education']
)
on conflict (id) do nothing;

insert into bill_chunks (bill_id, chunk_index, content, page_number, clause_ref)
values
  ('mock-1', 0, 'Section 1. This is placeholder extract text for local development only. Run the ingestion pipeline to load real bill text.', 1, 'Section 1'),
  ('mock-1', 1, 'Section 14. Placeholder clause text for citation testing.', 1, 'Section 14')
on conflict do nothing;

-- Real examples quoted verbatim in ofin-spec.md §2.4 (10th Assembly Order
-- Papers), inserted here as events only — no matching `bills` row, exactly
-- like the live layer behaves for bills not yet in the deep-text corpus.
insert into bill_events (bill_number, title, chamber, stage, sitting_date,
                          sponsors, order_paper_id, source_url)
values
  ('HB.2716',
   'A Bill for an Act to Establish the Department of State Services Research and Development in the Department of State Services and for Related Matters',
   'House of Representatives', 'Second Reading', '2026-04-23',
   array['Hon. Abbas Tajudeen', 'Hon. Austin Asama'],
   '11220', 'https://nass.gov.ng/documents/download/11220'),
  ('HB.2629',
   'A Bill for an Act to Establish the National Institute for Public Health and Infectious Diseases',
   'House of Representatives', 'Second Reading', '2026-04-23',
   array['Hon. Abbas Tajudeen', 'Hon. Amobi Ogah Godwin'],
   '11220', 'https://nass.gov.ng/documents/download/11220');
