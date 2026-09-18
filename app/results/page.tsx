import BillCard from "@/components/BillCard";
import { searchBills, getBillsByTopic } from "@/lib/queries";
import { Bill } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function ResultsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; topic?: string }>;
}) {
  const params = await searchParams;
  const q = params.q?.trim();
  const topic = params.topic?.trim();

  let bills: Bill[] = [];
  let error: string | null = null;

  try {
    if (topic) {
      bills = await getBillsByTopic(topic);
    } else if (q) {
      bills = await searchBills(q);
    }
  } catch (e) {
    error = e instanceof Error ? e.message : "Search failed.";
  }

  const heading = topic ? `Topic: ${topic}` : q ? `Results for "${q}"` : "Search";

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-bold">{heading}</h1>

      {error && <p className="caveat">{error}</p>}

      {!error && bills.length === 0 && (
        <p className="text-sm text-muted">No bills found. Try a different word or topic.</p>
      )}

      <div className="flex flex-col gap-3">
        {bills.map((b) => (
          <BillCard key={b.id} bill={b} />
        ))}
      </div>
    </div>
  );
}
