import logging
import subprocess
import tempfile
import os

from app.services.llm_service import generate_response

logger = logging.getLogger(__name__)

_CODER_PROMPT = """You are a Python execution agent.
Write a Python script to answer the user's request.
The script MUST print the final result to stdout using `print()`.

User Request: {query}

Output ONLY valid Python code. Do not include markdown formatting, backticks, or explanations. 
Just the raw python code."""

def execute_python_code(code: str) -> str:
    """
    Writes code to a temporary file, executes it, and returns stdout.
    """
    # Clean markdown backticks if the LLM leaked them
    if code.startswith("```python"):
        code = code[9:]
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    
    code = code.strip()

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name

        logger.info("Executing generated python script...")
        result = subprocess.run(
            ["python", temp_path],
            capture_output=True,
            text=True,
            timeout=10 # Prevent infinite loops
        )

        os.remove(temp_path)

        if result.returncode == 0:
            return f"Code executed successfully.\nOutput:\n{result.stdout}"
        else:
            return f"Code execution failed.\nError:\n{result.stderr}"

    except subprocess.TimeoutExpired:
        os.remove(temp_path)
        return "Error: Script execution timed out (exceeded 10 seconds)."
    except Exception as e:
        return f"Error running script: {e}"

def coder_node(state: dict) -> dict:
    """
    Generates and executes a Python script to solve a task.
    """
    query = state["query"]
    
    prompt = _CODER_PROMPT.format(query=query)
    
    logger.info("Generating python code for query: %s", query)
    code = generate_response(prompt, model=state.get("model"))
    
    result = execute_python_code(code)
    
    # Store both the code and the result in tool_results for the summarizer
    formatted_result = f"I wrote and executed this Python code:\n```python\n{code}\n```\n\nExecution Result:\n{result}"
    
    return {
        **state,
        "tool_results": formatted_result,
        # We manually route this to 'tools' so the summarizer handles it
        "routing_decision": "tools"
    }
