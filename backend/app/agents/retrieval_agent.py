from app.services.rag_service import retrieve_docs

def retrieval_node(state):

    query = state["query"]

    docs = retrieve_docs(query)

    context = "\n\n".join(
        [doc.page_content for doc in docs]
    )

    return {
        "retrieved_docs": context
    }