import json
from typing import Any


def normalize_llm_response(res: Any) -> str:
    """Normalizes any LLM or LangChain response object (str, AIMessage, dict, list, Pydantic model)
    into a clean text string suitable for persistence in PostgreSQL TEXT columns.
    """
    if res is None:
        return ""

    if isinstance(res, str):
        return res

    # If object has .content attribute (e.g. LangChain AIMessage / BaseMessage)
    if hasattr(res, "content"):
        content_val = getattr(res, "content")
        if content_val is not res:
            return normalize_llm_response(content_val)

    # If it's a list (e.g. Gemini/LangChain multi-block list of contents)
    if isinstance(res, list):
        parts = []
        for item in res:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    parts.append(str(item["text"]))
                elif "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(str(item["content"]))
                else:
                    parts.append(json.dumps(item))
            elif hasattr(item, "text"):
                parts.append(str(getattr(item, "text")))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p)

    # If it's a dict (e.g. structured output or response dict)
    if isinstance(res, dict):
        if "text" in res and isinstance(res["text"], str):
            return res["text"]
        if "content" in res and isinstance(res["content"], str):
            return res["content"]
        if "response" in res and isinstance(res["response"], str):
            return res["response"]
        if "message" in res and isinstance(res["message"], str):
            return res["message"]
        if "text" in res:
            return normalize_llm_response(res["text"])
        if "content" in res:
            return normalize_llm_response(res["content"])
        return json.dumps(res)

    # Pydantic or custom model
    if hasattr(res, "text") and isinstance(getattr(res, "text"), str):
        return getattr(res, "text")
    if hasattr(res, "content") and isinstance(getattr(res, "content"), str):
        return getattr(res, "content")

    return str(res)
