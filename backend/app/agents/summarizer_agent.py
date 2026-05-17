from app.services.llm_service import generate_response

def summarizer_node(state):

    query = state["query"]

    context = state["retrieved_docs"]

    prompt = f"""
    You are an intelligent AI assistant.

    Answer the user's question
    using ONLY the context below.

    Context:
    {context}

    Question:
    {query}
    """

    response = generate_response(prompt)

    return {
        "final_response": response
    }