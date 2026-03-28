
# NASA Systems Engineering Handbook — RAG QA System

## Overview
An open-source, production-ready Retrieval-Augmented Generation (RAG) pipeline for answering complex technical questions over the NASA Systems Engineering Handbook (SP-2016-6105 Rev2, ~270 pages). This system is designed to handle real-world document challenges: process diagrams, cross-chapter references, multi-page tables, hierarchical sections, and acronym-dense text.

---

## Architecture Overview

```
User Question
    │
    ▼
Acronym Expansion (Optional)
    │
    ▼
Semantic Retrieval (Vector Search)
    │
    ▼
Post-Filtering & Enrichment
    │
    ▼
Context Graph (Multi-hop)
    │
    ▼
LLM Answer Generation
    │
    ▼
Answer + Citations

(Offline/Batch Ingestion Pipeline)
    ├─ PDF Parsing (Docling + PyMuPDF4)
    ├─ Metadata Extraction (ToC, page mapping)
    ├─ Hierarchical Chunking
    ├─ Embedding & Vector Store (FAISS/Chroma)
    ├─ Cross-Reference Index & Acronym Dictionary
    └─ Evaluation Dataset
```

- **Frontend**: Simple web UI for chat and QA.
- **Backend**: Python FastAPI app with modular services for ingestion, chunking, embedding, retrieval, and LLM interaction.
- **Storage**: BM25 (JSON) and Chroma (vector DB) for document retrieval.
- **LLM**: Pluggable LLM client (e.g., Gemini, Llama2).

---

## How to Run the Application

### Prerequisites
- Python 3.10 or 3.11
- (Recommended) Create and activate a virtual environment (venv or conda)
- Install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

### Start the Backend API
```bash
cd backend
uvicorn app.main:app --reload
```

### Start the Frontend
Open `frontend/index.html` in your browser. (No build step required.)

### Ingest Documents
Use the API endpoint or scripts to ingest and process documents. See backend/app/api/routes/ingest.py for details.

---

## Key Design Decisions
- **Docling + PyMuPDF**: Docling is used for layout-aware PDF parsing; PyMuPDF is a fallback for images/diagrams.
- **Hierarchical Chunking**: Splits by section headings, not fixed tokens, to preserve context and enable precise citations.
- **Printed Page Citations**: Citations use printed page numbers, not PDF indices, for user-friendly references.
- **Open-Source Embeddings**: Uses sentence-transformers (all-MiniLM-L6-v2) by default; Gemini is optional for benchmarking.
- **Multi-hop Retrieval**: Supports cross-chapter reasoning via a section graph and explicit multi-hop logic.
- **Pluggable LLM**: Supports both local (Llama2) and API-based (Gemini) LLMs.
- **Schema-Driven**: Pydantic schemas for data validation and API consistency.

---

## Known Limitations & Failure Modes
- **LLM Hallucination**: The LLM may generate plausible but incorrect answers if retrieval is weak or context is insufficient.
- **Chunking Granularity**: Poor chunking can lead to missed context or irrelevant retrieval.
- **Citation Mapping**: Citations may not always map perfectly to source text, especially for diagrams or tables.
- **Resource Usage**: Large documents or many concurrent users may require backend and storage scaling.
- **Dependency on External APIs**: LLM and embedding services may require API keys and have rate limits.
- **PDF Parsing**: Some PDFs may not be parsed cleanly due to formatting or OCR errors.
- **Multi-hop Latency**: Complex queries spanning chapters may be slower due to graph traversal.

---

## References
- [Project GitHub Repository](https://github.com/kousalyamd11720/Complex_technical_manual_QA_system)
- [Docling Documentation](https://github.com/docling-project/docling)
- [PyMuPDF](https://pymupdf.readthedocs.io/)
- [LangChain RAG](https://python.langchain.com/docs/use_cases/retrieval_augmented_generation/)
- [LlamaIndex](https://gpt-index.readthedocs.io/)
- [sentence-transformers](https://www.sbert.net/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Chroma](https://www.trychroma.com/)
- [NASA Handbook](https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf)

For more details, see the code and comments in each module.
