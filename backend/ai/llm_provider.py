"""
LLM Provider Abstraction — GDPR-aware factory.

Picks the chat model based on LLM_PROVIDER env var:
  - "groq"        → Groq Cloud (default, US-hosted — flag for GDPR review)
  - "huggingface" → HuggingFace Inference API (EU-hosted endpoints available)
  - "mistral"     → Mistral La Plateforme (EU-hosted, EEA-compliant)
  - "ollama"      → Local Ollama (fully on-prem, no external transmission)

Centralizing the choice means switching providers is a one-line config change
instead of grepping the codebase for ChatGroq imports.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    display_name: str
    region: str
    is_eea: bool
    model_id: str
    notes: str


def _provider_name() -> str:
    return (os.getenv("LLM_PROVIDER") or "groq").lower().strip()


def get_provider_info() -> ProviderInfo:
    """Return metadata about the currently configured LLM provider."""
    name = _provider_name()
    if name == "huggingface":
        return ProviderInfo(
            name="huggingface",
            display_name="HuggingFace Inference",
            region="EU (configurable)",
            is_eea=True,
            model_id=os.getenv("HF_MODEL", "Qwen/Qwen2.5-72B-Instruct"),
            notes="HuggingFace Serverless Inference. Many models hostable in EU regions.",
        )
    if name == "ollama":
        return ProviderInfo(
            name="ollama",
            display_name="Ollama (local)",
            region="On-premise",
            is_eea=True,
            model_id=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            notes="Fully local inference. No candidate data leaves the host.",
        )
    if name == "mistral":
        return ProviderInfo(
            name="mistral",
            display_name="Mistral La Plateforme (EU)",
            region="EU (France)",
            is_eea=True,
            model_id=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
            notes="EEA-hosted. GDPR-compliant for EU candidate data.",
        )
    return ProviderInfo(
        name="groq",
        display_name="Groq Cloud",
        region="US",
        is_eea=False,
        model_id=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        notes="Fast inference but US-hosted. Review GDPR posture before processing EU PII.",
    )


def get_chat_llm(temperature: float = 0.01, max_tokens: int = 2048) -> Any:
    """
    Returns a LangChain-compatible chat LLM based on LLM_PROVIDER.

    Falls back to Groq if the requested provider's package is unavailable
    so the demo still runs without forcing a new dependency.
    """
    info = get_provider_info()

    if info.name == "huggingface":
        try:
            from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint  # type: ignore
        except ImportError:
            logger.warning("langchain_huggingface unavailable — falling back to Groq.")
        else:
            endpoint = HuggingFaceEndpoint(
                repo_id=info.model_id,
                huggingfacehub_api_token=os.getenv("HF_API_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN", ""),
                max_new_tokens=max_tokens,
                temperature=max(temperature, 0.01),
                task="text-generation",
            )
            return ChatHuggingFace(llm=endpoint)

    if info.name == "ollama":
        try:
            from langchain_community.chat_models import ChatOllama  # type: ignore
        except ImportError:
            logger.warning("langchain_community.ChatOllama unavailable — falling back to Groq.")
        else:
            return ChatOllama(
                model=info.model_id,
                temperature=temperature,
                num_predict=max_tokens,
                base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            )

    if info.name == "mistral":
        try:
            from langchain_mistralai import ChatMistralAI  # type: ignore
        except ImportError:
            logger.warning("langchain_mistralai unavailable — falling back to Groq.")
        else:
            return ChatMistralAI(
                model=info.model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=os.getenv("MISTRAL_API_KEY", ""),
            )

    from langchain_groq import ChatGroq  # type: ignore
    return ChatGroq(
        model=info.model_id,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=os.getenv("GROQ_API_KEY", ""),
    )


def get_provider_status() -> dict:
    """JSON-friendly dict for surfacing provider info to the UI."""
    info = get_provider_info()
    return {
        "provider": info.name,
        "display_name": info.display_name,
        "region": info.region,
        "is_eea": info.is_eea,
        "model_id": info.model_id,
        "notes": info.notes,
        "gdpr_warning": None if info.is_eea else (
            "Current LLM provider is hosted outside the EEA. "
            "Candidate text submitted to the model leaves EU jurisdiction. "
            "Set LLM_PROVIDER=mistral or LLM_PROVIDER=ollama to restore EEA-only processing."
        ),
    }
