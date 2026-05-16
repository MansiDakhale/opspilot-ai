from langchain_ollama import ChatOllama

# Explicitly pointing to the Windows Host Ollama service from inside Docker
llm = ChatOllama(
    model="llama3",
    base_url="http://host.docker.internal:11434",
    temperature=0.7
)

def generate_response(message: str) -> str:
    response = llm.invoke(message)
    return response.content