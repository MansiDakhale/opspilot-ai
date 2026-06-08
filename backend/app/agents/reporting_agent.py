import logging
import uuid
import os
from datetime import datetime

from app.services.llm_service import generate_response

logger = logging.getLogger(__name__)

_REPORT_PROMPT = """You are OpsPilot's advanced Reporting Agent.
Your job is to write a comprehensive, well-structured, and highly detailed markdown report answering the user's request.

Guidelines:
1. Use professional, analytical language.
2. Structure the document with appropriate Markdown headers (e.g. #, ##, ###).
3. Include an Executive Summary or Introduction at the top.
4. Break down complex topics into clear sections using bullet points, tables, and bold text.
5. Provide a conclusion or summary at the end.

Ensure the final output is ONLY valid markdown. Do not include introductory conversational text (e.g. "Here is the report").

User Request: {query}"""


def reporting_node(state: dict) -> dict:
    """
    Generates a detailed markdown report, saves it to the filesystem,
    and returns a download link to the user.
    """
    query = state["query"]
    
    logger.info("Reporting agent synthesizing report for query: %s", query)
    
    prompt = _REPORT_PROMPT.format(query=query)
    report_content = generate_response(prompt, model=state.get("model"))
    
    # Ensure the directory exists
    os.makedirs("uploads/reports", exist_ok=True)
    
    # Generate a unique file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_id = f"{timestamp}_{uuid.uuid4().hex[:8]}"
    filename = f"{file_id}.md"
    file_path = os.path.join("uploads", "reports", filename)
    
    # Save the report to disk
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    logger.info("Saved report to %s", file_path)
    
    # Create the download link.
    # We use the relative URL path /reports/filename which matches the FastAPI StaticFiles mount.
    download_url = f"http://localhost:8000/reports/{filename}"
    
    final_answer = (
        f"✅ **Report Generated Successfully**\n\n"
        f"I have created a comprehensive report based on your request. "
        f"You can view or download it here:\n"
        f"📄 [Download {filename}]({download_url})"
    )
    
    return {
        **state,
        "final_response": final_answer,
    }
