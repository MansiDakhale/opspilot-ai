import os
import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants  (all tunable via environment variables)
# ---------------------------------------------------------------------------

VECTOR_DB_DIR = os.path.join(
    os.getenv(
        "APP_DATA_DIR",
        str(Path(__file__).resolve().parents[2])
    ),
    "chroma_db"
)

# Retrieval
RETRIEVAL_K          = int(os.getenv("RAG_RETRIEVAL_K", "8"))          # fetch more candidates
MMR_FETCH_K          = int(os.getenv("RAG_MMR_FETCH_K", "20"))         # MMR candidate pool
MMR_LAMBDA           = float(os.getenv("RAG_MMR_LAMBDA", "0.6"))        # relevance vs diversity
MIN_RELEVANCE_SCORE  = float(os.getenv("RAG_MIN_RELEVANCE_SCORE", "0.20"))  # lowered; MiniLM cosine scores are naturally low
MAX_CONTEXT_TOKENS   = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "8000"))  # increased from 4000

# Chunking
CHUNK_SIZE           = int(os.getenv("RAG_CHUNK_SIZE", "800"))          # larger → richer semantic units
CHUNK_OVERLAP        = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))       # enough to preserve cross-boundary context

# OCR
ENABLE_OCR_FALLBACK  = os.getenv("RAG_ENABLE_OCR_FALLBACK", "true").lower() == "true"
OCR_ZOOM             = float(os.getenv("RAG_OCR_ZOOM", "2.0"))


# ---------------------------------------------------------------------------
# Shared singletons (lazy-initialised)
# ---------------------------------------------------------------------------

_embedding_model = None
_text_splitter   = None
_vectorstore     = None


def get_embedding_model() -> HuggingFaceEmbeddings:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model: all-MiniLM-L6-v2")
        _embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embedding_model


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    global _text_splitter
    if _text_splitter is None:
        _text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            # Split on paragraph breaks first, then sentences, then words
            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
        )
    return _text_splitter


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        os.makedirs(VECTOR_DB_DIR, exist_ok=True)
        _vectorstore = Chroma(
            persist_directory=VECTOR_DB_DIR,
            embedding_function=get_embedding_model(),
            collection_metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB vectorstore initialised at: %s", VECTOR_DB_DIR)
    return _vectorstore


# ---------------------------------------------------------------------------
# OCR fallback
# ---------------------------------------------------------------------------

def _ocr_pdf(file_path: str) -> list[Document]:
    """
    OCR a PDF into one LangChain Document per page.
    Used only when embedded-text extraction yields no usable text.
    """
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "OCR fallback requires pymupdf, pytesseract, and pillow."
        ) from exc

    ocr_documents: list[Document] = []
    pdf = fitz.open(file_path)

    try:
        for page_index, page in enumerate(pdf):
            pix = page.get_pixmap(
                matrix=fitz.Matrix(OCR_ZOOM, OCR_ZOOM),
                alpha=False,
            )
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            text  = pytesseract.image_to_string(image).strip()

            logger.info("OCR page %d: %d chars extracted.", page_index + 1, len(text))

            if text:
                ocr_documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "page": page_index + 1,
                            "extraction_method": "ocr",
                        },
                    )
                )
    finally:
        pdf.close()

    return ocr_documents


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def ingest_pdf(file_path: str) -> int:
    """
    Load a PDF, split into chunks, enrich metadata, and upsert into Chroma.

    Returns:
        int: number of chunks inserted.
    """
    resolved = str(Path(file_path).resolve())

    if not os.path.exists(resolved):
        raise FileNotFoundError(f"PDF not found: {resolved}")

    # --- Load ---
    loader    = PyPDFLoader(resolved)
    documents = loader.load()

    logger.info("Loaded %d page(s) from: %s", len(documents), resolved)

    # --- OCR fallback ---
    if ENABLE_OCR_FALLBACK and not any(d.page_content.strip() for d in documents):
        logger.info("No embedded text found. Running OCR fallback.")
        documents = _ocr_pdf(resolved)
        logger.info("OCR produced %d text-bearing page(s).", len(documents))

    # --- Prepend page header to each document so chunks retain page context ---
    filename    = os.path.basename(resolved)
    document_id = Path(filename).stem

    for doc in documents:
        page_num = doc.metadata.get("page", "?")
        if doc.page_content.strip():
            doc.page_content = f"[Document: {filename} | Page: {page_num}]\n\n{doc.page_content}"

    # --- Chunk ---
    chunks = get_text_splitter().split_documents(documents)
    chunks = [c for c in chunks if c.page_content.strip()]

    if not chunks:
        raise ValueError(
            "No valid text chunks extracted. The file may be image-only, encrypted, "
            "or otherwise unreadable. OCR fallback also found nothing."
        )

    logger.info("Split into %d chunks (chunk_size=%d, overlap=%d).",
                len(chunks), CHUNK_SIZE, CHUNK_OVERLAP)

    # --- Enrich metadata ---
    for chunk in chunks:
        chunk.metadata["source"]      = filename
        chunk.metadata["document_id"] = document_id
        chunk.metadata.setdefault("extraction_method", "embedded_text")
        chunk.metadata.setdefault("page", "N/A")

    # --- Upsert into Chroma (delete old chunks first) ---
    store = get_vectorstore()

    try:
        store.delete(where={"document_id": document_id})
        logger.info("Deleted previous chunks for document_id=%s.", document_id)
    except Exception as del_err:
        logger.info("No previous chunks to delete for %s: %s", document_id, del_err)

    store.add_documents(chunks)
    logger.info("Inserted %d chunks for %s.", len(chunks), filename)

    return len(chunks)


# ---------------------------------------------------------------------------
# Retrieval  — with MMR + relevance filtering + safe context assembly
# ---------------------------------------------------------------------------

def retrieve_docs(query: str, document_id: str | None = None) -> list[Document]:
    """
    Retrieve the most relevant, diverse document chunks for a query.

    Args:
        query:       The user's question.
        document_id: Optional. If provided, retrieval is scoped to that document only.
                     Pass the PDF stem (filename without .pdf extension).

    Returns:
        Ordered list of LangChain Document objects (best-first). May be empty.
    """
    store = get_vectorstore()

    # --- Build optional metadata filter ---
    search_kwargs: dict = {"k": RETRIEVAL_K, "fetch_k": MMR_FETCH_K, "lambda_mult": MMR_LAMBDA}

    if document_id:
        search_kwargs["filter"] = {"document_id": document_id}

    # --- MMR retrieval (Maximum Marginal Relevance) ---
    # MMR balances relevance AND diversity so we get richer context
    # instead of 8 near-identical chunks from the same paragraph.
    try:
        mmr_docs = store.max_marginal_relevance_search(
            query,
            **search_kwargs,
        )
    except Exception as exc:
        logger.error("MMR retrieval failed for query=%r: %s", query, exc)
        return []

    if not mmr_docs:
        logger.warning("MMR returned 0 docs for query=%r.", query)
        return []

    # --- Score each MMR result with a separate similarity lookup ---
    # max_marginal_relevance_search doesn't return scores directly,
    # so we do a quick scored search to tag each document with a relevance score.
    try:
        scored = store.similarity_search_with_relevance_scores(
            query,
            k=MMR_FETCH_K,
            **({"filter": {"document_id": document_id}} if document_id else {}),
        )
        score_map = {doc.page_content[:100]: score for doc, score in scored}
    except Exception:
        score_map = {}

    # --- Filter by relevance threshold & attach score ---
    filtered: list[Document] = []

    for doc in mmr_docs:
        score = score_map.get(doc.page_content[:100], 1.0)   # default=1.0 keeps doc if unknown
        doc.metadata["relevance_score"] = round(float(score), 4)

        if score >= MIN_RELEVANCE_SCORE:
            filtered.append(doc)
        else:
            logger.debug(
                "Dropped chunk (score=%.4f < %.4f): %s…",
                score, MIN_RELEVANCE_SCORE, doc.page_content[:80]
            )

    if not filtered:
        # Fall back: return top-3 MMR docs even below threshold, so the LLM
        # can still attempt a partial answer instead of a hard refusal.
        logger.warning(
            "All MMR docs scored below threshold %.2f for query=%r. "
            "Returning top-3 as fallback.",
            MIN_RELEVANCE_SCORE, query
        )
        for doc in mmr_docs[:3]:
            doc.metadata.setdefault("relevance_score", 0.0)
        filtered = mmr_docs[:3]

    # --- Ensure metadata defaults ---
    for doc in filtered:
        doc.metadata.setdefault("source",      "Uploaded PDF")
        doc.metadata.setdefault("page",        "N/A")
        doc.metadata.setdefault("document_id", "unknown")

    logger.info(
        "Returning %d/%d chunks for query=%r | scores=%s",
        len(filtered), len(mmr_docs), query,
        [d.metadata.get("relevance_score") for d in filtered],
    )

    return filtered


# ---------------------------------------------------------------------------
# Context assembly helper  (used by API layer)
# ---------------------------------------------------------------------------

def build_context(docs: list[Document], max_chars: int = MAX_CONTEXT_TOKENS) -> tuple[str, list[dict]]:
    """
    Turn retrieved documents into:
      - A numbered context string safe for the LLM prompt
      - A sources list for the API response

    Truncation is done *per-chunk* (not blind slice) so we never cut a chunk mid-word.
    """
    numbered_contexts: list[str] = []
    sources:           list[dict] = []
    total_chars = 0

    for idx, doc in enumerate(docs, start=1):
        snippet  = doc.page_content.strip()
        header   = (
            f"[SOURCE {idx} | {doc.metadata.get('source', 'Unknown')} "
            f"| Page: {doc.metadata.get('page', 'N/A')} "
            f"| Score: {doc.metadata.get('relevance_score', '?')}]"
        )
        block    = f"{header}\n{snippet}"
        block_len = len(block)

        if total_chars + block_len > max_chars:
            # Include a trimmed version of this chunk if we have room for at least 200 chars
            remaining = max_chars - total_chars
            if remaining > 200:
                trimmed = snippet[: remaining - len(header) - 10]
                numbered_contexts.append(f"{header}\n{trimmed}…")
                sources.append({
                    "id":              idx,
                    "content":         snippet[:300],
                    "source":          doc.metadata.get("source", "Unknown"),
                    "page":            doc.metadata.get("page", "N/A"),
                    "relevance_score": doc.metadata.get("relevance_score"),
                })
            logger.info("Context limit reached at source %d / %d.", idx, len(docs))
            break

        numbered_contexts.append(block)
        sources.append({
            "id":              idx,
            "content":         snippet[:300],
            "source":          doc.metadata.get("source", "Unknown"),
            "page":            doc.metadata.get("page", "N/A"),
            "relevance_score": doc.metadata.get("relevance_score"),
        })
        total_chars += block_len + 2   # +2 for "\n\n" separator

    context = "\n\n".join(numbered_contexts)
    return context, sources
