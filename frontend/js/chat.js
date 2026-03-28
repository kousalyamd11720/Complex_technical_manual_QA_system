import { ingest, query } from "./api.js";
import { renderAnswer, renderCitations } from "./render.js";
import { state } from "./state.js";

const ingestBtn = document.getElementById("ingestBtn");
const askBtn = document.getElementById("askBtn");
const pdfPathInput = document.getElementById("pdfPath");
const questionInput = document.getElementById("question");
const answerEl = document.getElementById("answer");
const citationsList = document.getElementById("citationsList");

ingestBtn.addEventListener("click", async () => {
  try {
    answerEl.textContent = "Ingesting PDF and building index...";
    const payload = await ingest(pdfPathInput.value.trim());
    answerEl.textContent = `Ingest complete. Records: ${payload.records_count}, Chunks: ${payload.chunks_count}`;
  } catch (err) {
    answerEl.textContent = `Ingest failed: ${err.message}`;
  }
});

askBtn.addEventListener("click", async () => {
  const question = questionInput.value.trim();
  if (!question) return;
  try {
    answerEl.textContent = "Querying...";
    const payload = await query(question, 8);
    state.currentQueryId = payload.query_id;
    state.lastResponse = payload;
    renderAnswer(answerEl, payload);
    renderCitations(citationsList, payload.citations || []);
  } catch (err) {
    answerEl.textContent = `Query failed: ${err.message}`;
  }
});
