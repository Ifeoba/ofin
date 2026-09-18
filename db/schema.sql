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
  status          text not null default 'scheduled' check (status <> 'passed'),
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
