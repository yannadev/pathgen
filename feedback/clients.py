"""Thin, lazy API clients for Pathgen's embedding and generation providers."""

from django.conf import settings
from groq import Groq
from openai import OpenAI


EMBEDDING_DIMENSIONS = 1536


def _required_setting(name):
    value = getattr(settings, name, "")
    if not value:
        raise RuntimeError(f"{name} is not configured.")
    return value


def embed_many(texts):
    """Embed non-empty text values in one OpenAI request, preserving order."""
    texts = list(texts)
    if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Embedding input must contain non-empty strings.")

    client = OpenAI(api_key=_required_setting("OPENAI_API_KEY"))
    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts,
    )
    ordered_data = sorted(response.data, key=lambda item: item.index)
    vectors = [list(item.embedding) for item in ordered_data]
    if len(vectors) != len(texts):
        raise ValueError("Embedding provider returned an unexpected result count.")
    if any(len(vector) != EMBEDDING_DIMENSIONS for vector in vectors):
        raise ValueError(
            f"Embedding vectors must contain {EMBEDDING_DIMENSIONS} dimensions."
        )
    return vectors


def embed(text):
    """Convert one query string to a 1536-dimensional embedding vector."""
    return embed_many([text])[0]


def generate_text(*, system_prompt, user_prompt):
    """Generate focused feedback through Groq using the configured model."""
    if not system_prompt.strip() or not user_prompt.strip():
        raise ValueError("Generation prompts cannot be empty.")
    client = Groq(api_key=_required_setting("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Generation provider returned empty feedback.")
    return content.strip()
