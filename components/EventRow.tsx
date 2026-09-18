import Link from "next/link";
import { BillEvent } from "@/lib/types";

function formatDate(d: string) {
  return new Date(d).toLocaleDateString("en-NG", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function EventRow({ event }: { event: BillEvent }) {
  const inner = (
    <div className="card flex flex-col gap-1">
      <span className="badge w-fit">Listed for {event.stage}</span>
      <p className="font-medium">{event.title}</p>
      <p className="text-sm text-muted">
        {event.bill_number} · {event.chamber} · {formatDate(event.sitting_date)}
      </p>
    </div>
  );

  return event.bill_id ? (
    <Link href={`/bills/${event.bill_id}`}>{inner}</Link>
  ) : (
    <a href={event.source_url} target="_blank" rel="noreferrer">
      {inner}
    </a>
  );
}
