import { WhatChanges } from "@/lib/types";

export default function ChangeItem({
  change,
  extract,
}: {
  change: WhatChanges;
  extract: string | null;
}) {
  return (
    <details className="card">
      <summary className="cursor-pointer list-none font-medium marker:hidden">
        {change.change}
        {change.clause_ref && (
          <span className="chip ml-2 !px-2 !py-0.5 text-xs">{change.clause_ref} ▸</span>
        )}
      </summary>
      <div className="mt-3 border-t border-border pt-3 text-sm text-muted">
        {extract ? (
          <p className="whitespace-pre-wrap">{extract}</p>
        ) : (
          <p>Extract not available for this citation.</p>
        )}
        {change.page && <p className="mt-2 text-xs">Page {change.page}</p>}
      </div>
    </details>
  );
}
