from app.workers.celery_app import celery

from app.services.rag_service import ingest_pdf

@celery.task
def process_pdf_task(file_path: str):

    chunks = ingest_pdf(file_path)

    return {
        "status": "completed",
        "chunks_created": chunks
    }