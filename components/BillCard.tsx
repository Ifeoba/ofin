import Link from "next/link";
import { Bill } from "@/lib/types";

export default function BillCard({ bill }: { bill: Bill }) {
  return (
    <Link href={`/bills/${bill.id}`} className="card flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-muted">
          {bill.bill_number ?? "No number"} · {bill.chamber}
        </span>
        <span className="badge">{bill.has_full_text ? "Full text available" : "Listed only"}</span>
      </div>
      <h3 className="font-semibold leading-snug">{bill.title}</h3>
      {bill.summary && <p className="line-clamp-2 text-sm text-muted">{bill.summary}</p>}
      {bill.topics && bill.topics.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {bill.topics.map((t) => (
            <span key={t} className="chip !px-2 !py-0.5 text-xs">
              {t}
            </span>
          ))}
        </div>
      )}
    </Link>
  );
}
