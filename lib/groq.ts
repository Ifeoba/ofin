const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
export const GROQ_MODEL = process.env.GROQ_MODEL || "openai/gpt-oss-120b";

interface GroqToolCallParams {
  prompt: string;
  toolName: string;
  toolDescription: string;
  parameters: Record<string, unknown>;
  maxTokens?: number;
}

/**
 * Ask Groq for a structured response via a forced tool call, instead of
 * "return only JSON" text parsing — the response is always well-formed and
 * matches `parameters` exactly, the same guarantee the Anthropic tool-use
 * calls this replaced were built for.
 */
export async function groqToolCall({
  prompt,
  toolName,
  toolDescription,
  parameters,
  maxTokens = 1500,
}: GroqToolCallParams): Promise<Record<string, any> | null> {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    throw new Error("GROQ_API_KEY is not set.");
  }

  const res = await fetch(GROQ_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: GROQ_MODEL,
      max_tokens: maxTokens,
      messages: [{ role: "user", content: prompt }],
      tools: [
        {
          type: "function",
          function: { name: toolName, description: toolDescription, parameters },
        },
      ],
      tool_choice: { type: "function", function: { name: toolName } },
    }),
  });

  if (!res.ok) {
    throw new Error(`Groq request failed: ${res.status} ${await res.text()}`);
  }

  const data = await res.json();
  const toolCall = data.choices?.[0]?.message?.tool_calls?.[0];
  if (!toolCall) return null;
  return JSON.parse(toolCall.function.arguments);
}
