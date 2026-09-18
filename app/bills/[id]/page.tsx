import { notFound } from "next/navigation";
import { getBillById, getChunkByRef, getEventsForBill } from "@/lib/queries";
import ChangeItem from "@/components/ChangeItem";
import EventRow from "@/components/EventRow";
import AskBox from "@/components/AskBox";
import { WhatChanges } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function BillPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const bill = await getBillById(id);
  if (!bill) notFound();

  const events = await getEventsForBill(bill.id, bill.bill_number);
  const whatChanges = (bill.what_changes ?? []) as WhatChanges[];
  const extracts = await Promise.all(
    whatChanges.map((c) => getChunkByRef(bill.id, c.clause_ref, c.page))
  );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <span className="badge">{bill.has_full_text ? "Full text available" : "Listed only"}</span>
        <h1 className="mt-2 text-2xl font-bold leading-tight">{bill.title}</h1>
        <p className="mt-1 text-sm text-muted">
          {bill.bill_number ?? "No bill number"} · {bill.chamber}
        </p>
      </div>

      {bill.summary && (
        <section>
          <h2 className="mb-2 text-lg font-semibold">What is this?</h2>
          <p>{bill.summary}</p>
        </section>
      )}

      {bill.why_introduced && (
        <section>
          <h2 className="mb-2 text-lg font-semibold">Why was it introduced?</h2>
          <p>{bill.why_introduced}</p>
        </section>
      )}

      {whatChanges.length > 0 && (
        <section className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">What would change?</h2>
          {whatChanges.map((c, i) => (
            <ChangeItem key={i} change={c} extract={extracts[i]?.content ?? null} />
          ))}
        </section>
      )}

      {bill.who_affected && bill.who_affected.length > 0 && (
        <section>
          <h2 className="mb-2 text-lg font-semibold">Who could this affect?</h2>
          <div className="flex flex-wrap gap-2">
            {bill.who_affected.map((w) => (
              <span key={w} className="chip">
                {w}
              </span>
            ))}
          </div>
        </section>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Where is it?</h2>
        <p className="caveat">
          Order Papers record scheduled business, not outcomes. Confirmation appears in Votes
          &amp; Proceedings, which Òfin does not yet parse.
        </p>
        {events.length === 0 ? (
          <p className="text-sm text-muted">No Order Paper activity recorded for this bill yet.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {events.map((e) => (
              <EventRow key={e.id} event={e} />
            ))}
          </div>
        )}
      </section>

      <section>
        <a href={bill.source_url} target="_blank" rel="noreferrer" className="chip">
          Read the original ↗
        </a>
      </section>

      {bill.has_full_text && (
        <section className="flex flex-col gap-3 border-t border-border pt-6">
          <h2 className="text-lg font-semibold">Ask about this bill</h2>
          <AskBox billId={bill.id} />
        </section>
      )}
    </div>
  );
}
