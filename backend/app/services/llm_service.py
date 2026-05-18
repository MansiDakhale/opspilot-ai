from langchain_ollama import ChatOllama

from langchain_core.messages import (
    HumanMessage,
    SystemMessage
)

llm = ChatOllama(
    model="phi3:mini",
    temperature=0.3,
    base_url="http://host.docker.internal:11434",
    num_ctx=2048
)

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
- Give concise and accurate technical responses
- Use markdown formatting
- Use bullet points where useful
- Avoid repetition
- Do not hallucinate fake facts
- If uncertain, clearly say so
"""

def generate_response(message: str):

    messages = [

        SystemMessage(
            content=SYSTEM_PROMPT
        ),

        HumanMessage(
            content=message
        )
    ]

    response = llm.invoke(messages)

    return response.content


async def stream_response(message: str):

    messages = [

        SystemMessage(
            content=SYSTEM_PROMPT
        ),

        HumanMessage(
            content=message
        )
    ]

    async for chunk in llm.astream(messages):

        if chunk.content:

            yield chunk.content