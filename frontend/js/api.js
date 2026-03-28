import { state } from "./state.js";

export async function ingest(pdfPath) {
  const resp = await fetch(`${state.apiBase}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pdf_path: pdfPath, rebuild_index: true }),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function query(question, topK = 8) {
  const resp = await fetch(`${state.apiBase}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function getCitations(queryId) {
  const resp = await fetch(`${state.apiBase}/citations/${queryId}`);
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}
