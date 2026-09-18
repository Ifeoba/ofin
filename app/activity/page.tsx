import Link from "next/link";
import EventRow from "@/components/EventRow";
import { getEvents } from "@/lib/queries";

export const dynamic = "force-dynamic";

const CHAMBERS = ["Senate", "House of Representatives"];

export default async function ActivityPage({
  searchParams,
}: {
  searchParams: Promise<{ chamber?: string }>;
}) {
  const params = await searchParams;
  const chamber = params.chamber ?? null;
  const events = await getEvents(chamber, 50).catch(() => []);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-bold">Activity</h1>
      <p className="caveat">
        Order Papers record scheduled business, not outcomes. Every item below is
        &ldquo;Listed for&rdquo; a stage — not passed, not approved.
      </p>

      <div className="flex gap-2">
        <Link href="/activity" className={`chip ${!chamber ? "bg-accent text-white" : ""}`}>
          All
        </Link>
        {CHAMBERS.map((c) => (
          <Link
            key={c}
            href={`/activity?chamber=${encodeURIComponent(c)}`}
            className={`chip ${chamber === c ? "bg-accent text-white" : ""}`}
          >
            {c}
          </Link>
        ))}
      </div>

      <div className="flex flex-col gap-2">
        {events.length === 0 && <p className="text-sm text-muted">No events ingested yet.</p>}
        {events.map((e) => (
          <EventRow key={e.id} event={e} />
        ))}
      </div>
    </div>
  );
}
