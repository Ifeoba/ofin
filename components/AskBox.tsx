"use client";

import { useState, FormEvent } from "react";
import { AskResponse } from "@/lib/types";

export default function AskBox({ billId }: { billId: string }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ billId, question }),
      });
      if (!res.ok) throw new Error("Request failed");
      const data: AskResponse = await res.json();
      setResult(data);
    } catch {
      setError("Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <form onSubmit={submit} className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about this bill..."
          maxLength={500}
          className="flex-1 rounded-lg border border-border px-4 py-3 text-base"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-accent px-4 py-3 font-semibold text-white disabled:opacity-50"
        >
          {loading ? "Asking..." : "Ask"}
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {result && (
        <div className={`card ${result.grounded ? "" : "opacity-70"}`}>
          <p className={result.grounded ? "font-medium" : "italic text-muted"}>{result.answer}</p>
          {result.grounded && result.citations?.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {result.citations.map((c, i) => (
                <span key={i} className="chip !px-2 !py-0.5 text-xs" title={c.quote}>
                  {c.clause_ref ?? (c.page ? `p. ${c.page}` : "source")}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
