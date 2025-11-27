"""Factory helpers to construct chat models based on the configured provider."""

from __future__ import annotations

from typing import Optional

from config import Config

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:  # pragma: no cover
    ChatAnthropic = None

try:
    from langchain_community.chat_models import ChatOllama
except ImportError:  # pragma: no cover
    ChatOllama = None


def get_chat_model(temperature: float = 0.4):
    """Return a configured chat model instance or None if unavailable."""
    provider = (Config.LLM_PROVIDER or "openai").lower()

    if provider == "openai" and Config.OPENAI_API_KEY and ChatOpenAI:
        return ChatOpenAI(api_key=Config.OPENAI_API_KEY, model=Config.OPENAI_MODEL, temperature=temperature)

    if provider == "anthropic" and Config.ANTHROPIC_API_KEY and ChatAnthropic:
        return ChatAnthropic(api_key=Config.ANTHROPIC_API_KEY, model=Config.ANTHROPIC_MODEL, temperature=temperature)

    if provider == "ollama" and ChatOllama:
        return ChatOllama(base_url=Config.OLLAMA_BASE_URL, model=Config.OLLAMA_MODEL, temperature=temperature)

    if provider == "qwen" and Config.DASHSCOPE_API_KEY and ChatOpenAI:
        return ChatOpenAI(
            api_key=Config.DASHSCOPE_API_KEY,
            base_url=Config.DASHSCOPE_BASE_URL,
            model=Config.QWEN_MODEL,
            temperature=temperature,
        )

    if provider == "deepseek" and Config.DEEPSEEK_API_KEY and ChatOpenAI:
        return ChatOpenAI(
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.DEEPSEEK_API_BASE,
            model=Config.DEEPSEEK_MODEL,
            temperature=temperature,
        )

    return None

