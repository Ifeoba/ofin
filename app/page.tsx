import Link from "next/link";
import { getRecentEvents } from "@/lib/queries";
import EventRow from "@/components/EventRow";

export const dynamic = "force-dynamic";

const TOPICS = ["education", "health", "tax", "electricity", "children", "security"];

export default async function HomePage() {
  const events = await getRecentEvents(5).catch(() => []);

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-3">
        <h1 className="text-2xl font-bold">What do you want to understand?</h1>
        <form action="/results" method="get" className="flex gap-2">
          <input
            name="q"
            type="search"
            placeholder="e.g. school fees, electricity, small business tax"
            className="flex-1 rounded-lg border border-border px-4 py-3 text-base"
            autoFocus
          />
          <button
            type="submit"
            className="rounded-lg bg-accent px-4 py-3 font-semibold text-white"
          >
            Search
          </button>
        </form>
        <div className="flex flex-wrap gap-2">
          {TOPICS.map((t) => (
            <Link key={t} href={`/results?topic=${t}`} className="chip">
              {t}
            </Link>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">This week in the National Assembly</h2>
        {events.length === 0 ? (
          <p className="text-sm text-muted">
            No activity ingested yet. Run the ingestion pipeline to populate this feed.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {events.map((e) => (
              <EventRow key={e.id} event={e} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
