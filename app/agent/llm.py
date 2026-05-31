"""Shared LLM client factory for the agent nodes.

All LLM-backed nodes (strategy, research, reflection) share one lazily-built
ChatGroq client so a single ``set_llm`` injection in a test covers the whole
graph. The client is built on first use (not at import) to preserve the
no-import-side-effects rule established in Phase 0.
"""

from typing import Optional

from langchain_groq import ChatGroq

from app.config import get_settings

import json
import re

_llm: Optional[object] = None


def get_llm():
    """Return the process-wide chat LLM, creating it lazily on first use."""
    global _llm
    if _llm is None:
        settings = get_settings()
        _llm = ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.2,
        )
    return _llm


def set_llm(llm) -> None:
    """Test seam: inject a fake LLM (anything with ``ainvoke``) or reset with ``None``."""
    global _llm
    _llm = llm


def content_to_text(content) -> str:
    """Normalize a LangChain message ``content`` into a plain string.

    ``content`` may be a string, or a list of content blocks where each block is
    either a string or a dict (e.g. ``{"type": "text", "text": "..."}``).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text") or block.get("content") or "")
        return "".join(parts)
    return str(content)


def extract_json_object(text: str) -> Optional[dict]:
    """Parse the first JSON object from raw LLM text, tolerating fences/prose.

    Returns the parsed dict, or ``None`` if no valid JSON object is found. Never
    raises -- callers supply their own safe fallback.
    """
    cleaned = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    candidate = match.group(0) if match else cleaned
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


async def ainvoke_text(prompt: str) -> str:
    """Invoke the shared LLM and return its content normalized to text."""
    response = await get_llm().ainvoke(prompt)
    return content_to_text(getattr(response, "content", response))


__all__ = [
    "get_llm",
    "set_llm",
    "content_to_text",
    "extract_json_object",
    "ainvoke_text",
]
