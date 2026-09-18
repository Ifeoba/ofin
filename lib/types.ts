export interface WhatChanges {
  change: string;
  clause_ref: string | null;
  page: number | null;
}

export interface Bill {
  id: string;
  bill_number: string | null;
  title: string;
  chamber: string;
  source_url: string;
  has_full_text: boolean;
  full_text: string | null;
  page_count: number | null;
  summary: string | null;
  why_introduced: string | null;
  what_changes: WhatChanges[] | null;
  who_affected: string[] | null;
  topics: string[] | null;
  created_at: string;
}

export interface BillEvent {
  id: number;
  bill_id: string | null;
  bill_number: string;
  title: string;
  chamber: string;
  stage: string;
  status: string;
  sitting_date: string;
  sponsors: string[] | null;
  order_paper_id: string;
  source_url: string;
}

export interface BillChunk {
  id: number;
  bill_id: string;
  chunk_index: number;
  content: string;
  page_number: number | null;
  clause_ref: string | null;
}

export interface AskCitation {
  clause_ref?: string;
  page?: number;
  quote: string;
}

export interface AskResponse {
  answer: string;
  citations: AskCitation[];
  grounded: boolean;
}
