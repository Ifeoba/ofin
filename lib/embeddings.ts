const VOYAGE_URL = "https://api.voyageai.com/v1/embeddings";
const VOYAGE_MODEL = "voyage-2"; // 1024-dim, matches the `vector(1024)` columns

export function embeddingsAvailable(): boolean {
  return Boolean(process.env.VOYAGE_API_KEY);
}

export async function embed(
  text: string,
  inputType: "query" | "document" = "query"
): Promise<number[]> {
  const apiKey = process.env.VOYAGE_API_KEY;
  if (!apiKey) {
    throw new Error("VOYAGE_API_KEY is not set.");
  }
  const res = await fetch(VOYAGE_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ input: text, model: VOYAGE_MODEL, input_type: inputType }),
  });
  if (!res.ok) {
    throw new Error(`Voyage embedding failed: ${res.status} ${await res.text()}`);
  }
  const data = await res.json();
  return data.data[0].embedding as number[];
}

export function toPgVector(vec: number[]): string {
  return `[${vec.join(",")}]`;
}
