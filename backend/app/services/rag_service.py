import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Ensure data survives inside the workspace
VECTOR_DB_DIR = os.path.join(os.getcwd(), "chroma_db")

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

def ingest_pdf(file_path: str) -> int:
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    chunks = text_splitter.split_documents(documents)
    
    # In modern LangChain, data is auto-persisted on instantiation
    Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=VECTOR_DB_DIR
    )
    
    return len(chunks)

def retrieve_docs(query: str):
    vectorstore = Chroma(
        persist_directory=VECTOR_DB_DIR,
        embedding_function=embedding_model
    )
    
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    return retriever.invoke(query)