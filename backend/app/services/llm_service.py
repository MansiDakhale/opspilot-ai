from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

llm = ChatOllama(
    model="phi3:mini",
    temperature=0.3,
    base_url="http://host.docker.internal:11434",
    num_ctx=2048
)

print("USING MODEL:", llm.model)

SYSTEM_PROMPT = """
You are OpsPilot AI, a professional AI engineering assistant.

You specialize in:
- AI Engineering
- FastAPI
- LangChain
- LangGraph
- RAG systems
- Vector databases
- Agentic AI
- LLM infrastructure
- Python backend engineering

Rules:
- Give concise and accurate technical responses.
- Use markdown formatting.
- Use bullet points where useful.
- Avoid repetition.
- Do not hallucinate fake facts.
- If uncertain, clearly say so.
- Focus on practical engineering explanations.
- LangGraph is a Python framework for building stateful multi-agent AI workflows developed by LangChain.
- Only answer using provided context.
- Do not infer unrelated information.
- If information is missing, say so.
"""

def generate_response(message: str):

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message)
    ]

    response = llm.invoke(messages)

    return response.content