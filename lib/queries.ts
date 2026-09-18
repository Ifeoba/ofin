import { query } from "./db";
import { embed, embeddingsAvailable, toPgVector } from "./embeddings";
import { Bill, BillChunk, BillEvent } from "./types";

export async function getRecentEvents(limit = 5): Promise<BillEvent[]> {
  return query<BillEvent>(
    `select * from bill_events order by sitting_date desc, id desc limit $1`,
    [limit]
  );
}

export async function getEvents(chamber: string | null, limit = 50): Promise<BillEvent[]> {
  if (chamber) {
    return query<BillEvent>(
      `select * from bill_events where chamber = $1 order by sitting_date desc, id desc limit $2`,
      [chamber, limit]
    );
  }
  return query<BillEvent>(
    `select * from bill_events order by sitting_date desc, id desc limit $1`,
    [limit]
  );
}

export async function searchBills(q: string, limit = 12): Promise<Bill[]> {
  if (embeddingsAvailable()) {
    const vec = await embed(q, "query");
    return query<Bill>(
      `select * from bills where embedding is not null
       order by embedding <=> $1::vector limit $2`,
      [toPgVector(vec), limit]
    );
  }
  // No VOYAGE_API_KEY configured — fall back to a plain text match.
  return query<Bill>(
    `select * from bills
     where title ilike $1 or summary ilike $1
     order by created_at desc limit $2`,
    [`%${q}%`, limit]
  );
}

export async function getBillsByTopic(topic: string, limit = 12): Promise<Bill[]> {
  return query<Bill>(
    `select * from bills where topics @> array[$1]::text[] order by created_at desc limit $2`,
    [topic, limit]
  );
}

export async function getBillById(id: string): Promise<Bill | null> {
  const rows = await query<Bill>(`select * from bills where id = $1`, [id]);
  return rows[0] ?? null;
}

export async function getEventsForBill(
  billId: string,
  billNumber: string | null
): Promise<BillEvent[]> {
  if (billNumber) {
    return query<BillEvent>(
      `select * from bill_events where bill_id = $1 or bill_number = $2
       order by sitting_date desc`,
      [billId, billNumber]
    );
  }
  return query<BillEvent>(
    `select * from bill_events where bill_id = $1 order by sitting_date desc`,
    [billId]
  );
}

export async function getChunksForQuestion(
  billId: string,
  questionVec: number[] | null,
  limit = 8
): Promise<BillChunk[]> {
  if (questionVec) {
    return query<BillChunk>(
      `select * from bill_chunks where bill_id = $1
       order by embedding <=> $2::vector limit $3`,
      [billId, toPgVector(questionVec), limit]
    );
  }
  // No embedding available for the question (or for the chunks) — fall back
  // to reading the bill's chunks in document order.
  return query<BillChunk>(
    `select * from bill_chunks where bill_id = $1 order by chunk_index limit $2`,
    [billId, 40]
  );
}

export async function getChunkByRef(
  billId: string,
  clauseRef: string | null,
  page: number | null
): Promise<BillChunk | null> {
  if (clauseRef) {
    const rows = await query<BillChunk>(
      `select * from bill_chunks where bill_id = $1 and clause_ref = $2 limit 1`,
      [billId, clauseRef]
    );
    if (rows[0]) return rows[0];
  }
  if (page) {
    const rows = await query<BillChunk>(
      `select * from bill_chunks where bill_id = $1 and page_number = $2 limit 1`,
      [billId, page]
    );
    if (rows[0]) return rows[0];
  }
  return null;
}
