import { NextRequest, NextResponse } from "next/server";
import type Anthropic from "@anthropic-ai/sdk";
import { ASK_MODEL, getAnthropic } from "@/lib/anthropic";
import { embed, embeddingsAvailable } from "@/lib/embeddings";
import { getBillById, getChunksForQuestion } from "@/lib/queries";
import { AskResponse } from "@/lib/types";

const ASK_TOOL: Anthropic.Tool = {
  name: "answer_bill_question",
  description: "Answer a citizen's question about a bill using only the provided extracts.",
  input_schema: {
    type: "object",
    properties: {
      answer: { type: "string" },
      citations: {
        type: "array",
        items: {
          type: "object",
          properties: {
            clause_ref: { type: "string" },
            page: { type: "integer" },
            quote: { type: "string" },
          },
          required: ["quote"],
        },
      },
      grounded: { type: "boolean" },
    },
    required: ["answer", "citations", "grounded"],
  },
};

const PROMPT = `Answer the user's question using ONLY the bill extracts below.

Hard rules:
- If the extracts do not answer the question, set "grounded" to false and make
  "answer" exactly: "This bill does not address that."
  Do not guess. Do not use outside knowledge of Nigerian law.
- Every factual claim in "answer" must have a matching citation.
- If the answer is partial, say what the bill DOES cover and what it does not.
- Never state whether the bill is law. Never predict whether it will pass.

BILL: {title} ({bill_number})
EXTRACTS:
{chunks}

QUESTION: {question}`;

const FALLBACK: AskResponse = {
  answer: "This bill does not address that.",
  citations: [],
  grounded: false,
};

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  const billId: string | undefined = body?.billId;
  const question: string | undefined = body?.question?.trim();

  if (!billId || !question || question.length > 500) {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 });
  }

  const bill = await getBillById(billId);
  if (!bill || !bill.has_full_text) {
    return NextResponse.json(FALLBACK);
  }

  let questionVec: number[] | null = null;
  if (embeddingsAvailable()) {
    try {
      questionVec = await embed(question, "query");
    } catch {
      questionVec = null;
    }
  }

  const chunks = await getChunksForQuestion(bill.id, questionVec, 8);
  if (chunks.length === 0) {
    return NextResponse.json(FALLBACK);
  }

  const chunkText = chunks
    .map((c) => `[${c.clause_ref ?? `p.${c.page_number ?? "?"}`}] ${c.content}`)
    .join("\n\n---\n\n");

  const prompt = PROMPT.replace("{title}", bill.title)
    .replace("{bill_number}", bill.bill_number ?? "")
    .replace("{chunks}", chunkText)
    .replace("{question}", question);

  try {
    const client = getAnthropic();
    const resp = await client.messages.create({
      model: ASK_MODEL,
      max_tokens: 1024,
      tools: [ASK_TOOL],
      tool_choice: { type: "tool", name: "answer_bill_question" },
      messages: [{ role: "user", content: prompt }],
    });

    const toolUse = resp.content.find(
      (b): b is Anthropic.ToolUseBlock => b.type === "tool_use"
    );
    if (!toolUse) {
      return NextResponse.json(FALLBACK);
    }

    return NextResponse.json(toolUse.input as AskResponse);
  } catch (err) {
    console.error("ask-a-bill failed", err);
    return NextResponse.json(FALLBACK, { status: 200 });
  }
}
