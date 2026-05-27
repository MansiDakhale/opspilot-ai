from app.services.llm_service import generate_response

def summarizer_node(state):

    query = state["query"]

    context = state["retrieved_docs"]

    if not context.strip():

        return {
            "final_response": "I could not find this information in the uploaded documents."
        }

    prompt = f"""
    You are an intelligent AI assistant.

    Answer the user's question
    using ONLY the context below. If the answer is not present in the context,
    reply exactly:
    "I could not find this information in the uploaded documents."

    Context:
    {context}

    Question:
    {query}
    """

    response = generate_response(prompt)

    return {
        "final_response": response
    }
