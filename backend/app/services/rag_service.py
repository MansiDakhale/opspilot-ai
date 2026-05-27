import os
import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# ---------------------------------------------------------------------------
# Logging
# NOTE: avoid configuring root logging at import time; main application
# should configure logging once on startup.
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VECTOR_DB_DIR = os.path.join(
    os.getenv(
        "APP_DATA_DIR",
        str(Path(__file__).resolve().parents[2])
    ),
    "chroma_db"
)

RETRIEVAL_K = int(os.getenv("RAG_RETRIEVAL_K", "6"))
MIN_RELEVANCE_SCORE = float(os.getenv("RAG_MIN_RELEVANCE_SCORE", "0.45"))


# ---------------------------------------------------------------------------
# Shared singletons (lazy-initialised)
# Create heavy objects only when needed to avoid slow/crashy imports.
# ---------------------------------------------------------------------------

embedding_model = None
text_splitter = None
vectorstore = None


def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return embedding_model


def get_text_splitter():
    global text_splitter
    if text_splitter is None:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=80
        )
    return text_splitter


def get_vectorstore():
    global vectorstore
    if vectorstore is None:
        os.makedirs(VECTOR_DB_DIR, exist_ok=True)
        embedding = get_embedding_model()
        vectorstore = Chroma(
            persist_directory=VECTOR_DB_DIR,
            embedding_function=embedding,
            collection_metadata={"hnsw:space": "cosine"}
        )
    return vectorstore


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def ingest_pdf(file_path: str) -> int:
    """
    Load a PDF, split it into chunks, enrich metadata, and upsert into Chroma.

    Returns:
        int: number of chunks inserted.

    Raises:
        ValueError: if the PDF yields no valid text chunks.
        Exception:  re-raises any Chroma insertion error.
    """

    resolved_file_path = str(Path(file_path).resolve())

    if not os.path.exists(resolved_file_path):
        raise FileNotFoundError(f"PDF not found for ingestion: {resolved_file_path}")

    loader = PyPDFLoader(resolved_file_path)
    documents = loader.load()

    logger.info("=== RAW DOCUMENTS ===")
    logger.info("Total documents loaded: %d", len(documents))

    for i, doc in enumerate(documents):
        logger.info("Document %d preview: %s", i + 1, doc.page_content[:500])

    # Split and filter empty chunks
    chunks = get_text_splitter().split_documents(documents)
    chunks = [c for c in chunks if c.page_content.strip()]

    if not chunks:
        raise ValueError("No valid text chunks extracted from PDF.")

    logger.info("=== CHUNK STATS ===")
    logger.info("Total chunks after splitting: %d", len(chunks))

    # Enrich metadata
    filename = os.path.basename(resolved_file_path)
    document_id = Path(filename).stem

    for chunk in chunks:
        chunk.metadata["source"] = filename
        chunk.metadata["document_id"] = document_id
        chunk.metadata.setdefault("page", "N/A")

    # Insert into Chroma
    try:
        get_vectorstore().add_documents(chunks)

        logger.info("Successfully inserted %d chunks into Chroma.", len(chunks))

    except Exception as e:
        logger.error("Chroma insertion failed: %s", str(e))
        raise

    # FIX: return is now outside the try/except — was unreachable before
    return len(chunks)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve_docs(query: str) -> list:
    """
    Retrieve the most relevant document chunks for a given query.

    Returns:
        list: list of LangChain Document objects (may be empty).
    """

    scored_docs = get_vectorstore().similarity_search_with_relevance_scores(
        query,
        k=RETRIEVAL_K
    )

    docs = []

    for doc, score in scored_docs:
        doc.metadata["relevance_score"] = round(float(score), 4)

        if score >= MIN_RELEVANCE_SCORE:
            docs.append(doc)

    if not docs:
        logger.warning(
            "No relevant documents found for query=%r. Best scores=%s",
            query,
            [round(float(score), 4) for _, score in scored_docs]
        )
        return []

    logger.info("=== RETRIEVED DOCS ===")

    for i, doc in enumerate(docs):
        logger.info(
            "Doc %d | Score: %s | Source: %s | Page: %s | Content: %s",
            i + 1,
            doc.metadata.get("relevance_score"),
            doc.metadata.get("source"),
            doc.metadata.get("page"),
            doc.page_content[:300]
        )

    # Ensure metadata keys are always present
    for doc in docs:
        doc.metadata.setdefault("source", "Uploaded PDF")
        doc.metadata.setdefault("page", "N/A")
        doc.metadata.setdefault("document_id", "unknown")

    return docs
