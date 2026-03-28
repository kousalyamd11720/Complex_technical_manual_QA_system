export function renderAnswer(container, payload) {
  container.textContent = `${payload.answer}\n\nConfidence: ${payload.confidence}`;
}

export function renderCitations(listEl, citations) {
  listEl.innerHTML = "";
  citations.forEach((c) => {
    const li = document.createElement("li");
    li.textContent = `${c.section || "n/a"} | printed p.${c.printed_page_label || "?"} | pdf p.${c.pdf_page_index ?? "?"} | ${c.reason}`;
    li.title = c.text || "";
    listEl.appendChild(li);
  });
}
