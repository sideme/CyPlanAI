"\"\"\"Utility helpers to generate human-friendly chat thread titles.\"\"\""

from __future__ import annotations

import re
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from services.llm_factory import get_chat_model


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def _heuristic_title(user_text: str, assistant_text: str) -> str:
    base = _clean_text(user_text) or _clean_text(assistant_text) or "New conversation"
    # Use the first sentence or first 6 words
    sentence_end = re.search(r"[.!?]", base)
    if sentence_end and sentence_end.start() < 80:
        base = base[: sentence_end.start()]
    words = base.split()
    if len(words) > 8:
        base = " ".join(words[:8])
    if len(base) > 64:
        base = f"{base[:61].rstrip()}..."
    return base.title()


def generate_conversation_title(user_text: str, assistant_text: str) -> str:
    """
    Generate a concise title based on the first user and assistant turns.
    Falls back to simple heuristics if no LLM is configured.
    """
    llm = get_chat_model(temperature=0.2)
    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        (
                            "You generate short conversation titles (at most 6 words). "
                            "Return only the title without quotes."
                        ),
                    ),
                    (
                        "human",
                        (
                            "Human: {user}\n"
                            "Assistant: {assistant}\n"
                            "Title:"
                        ),
                    ),
                ]
            )
            chain = prompt | llm | StrOutputParser()
            title = chain.invoke({"user": user_text, "assistant": assistant_text}).strip()
            clean_title = _clean_text(title)
            if clean_title:
                if len(clean_title) > 64:
                    clean_title = f"{clean_title[:61].rstrip()}..."
                return clean_title
        except Exception:  # pragma: no cover - best effort
            pass

    return _heuristic_title(user_text, assistant_text)

