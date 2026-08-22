"""Lesson-scoped dense retrieval over the generated JSON embedding index."""

import json
from pathlib import Path

from django.conf import settings
import numpy as np

from feedback import clients


def build_query(wrong_questions):
    """Build the embedding query from wrong question text and teaching hints."""
    parts = []
    for item in wrong_questions:
        question_text = item.get("question_text", "").strip()
        hint_text = item.get("hint_text", "").strip()
        if question_text or hint_text:
            parts.append(f"{question_text} {hint_text}".strip())
    query = " ".join(parts)
    if not query:
        raise ValueError("Retrieval requires at least one wrong question.")
    return query


def cosine_similarity(left, right):
    """Return cosine similarity for same-sized, non-zero numpy vectors."""
    left_vector = np.asarray(left, dtype=float)
    right_vector = np.asarray(right, dtype=float)
    if left_vector.ndim != 1 or right_vector.ndim != 1:
        raise ValueError("Embedding vectors must be one-dimensional.")
    if left_vector.shape != right_vector.shape:
        raise ValueError("Embedding vectors must use the same dimensions.")
    denominator = np.linalg.norm(left_vector) * np.linalg.norm(right_vector)
    if denominator == 0:
        raise ValueError("Embedding vectors cannot have zero magnitude.")
    return float(np.dot(left_vector, right_vector) / denominator)


def load_index(index_path=None):
    path = Path(index_path or Path(settings.BASE_DIR) / "seed_data" / "lesson_embeddings.json")
    try:
        chunks = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(f"RAG index is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"RAG index contains invalid JSON: {path}") from error
    if not isinstance(chunks, list):
        raise ValueError("RAG index must contain a JSON array.")
    return chunks


def retrieve(
    session_lesson_ids,
    wrong_questions,
    *,
    top_k=4,
    index_path=None,
    embed_fn=None,
):
    """Embed a misconception query and return its top lesson-scoped chunks."""
    if top_k <= 0:
        raise ValueError("top_k must be positive.")
    lesson_ids = {str(lesson_id) for lesson_id in session_lesson_ids}
    if not lesson_ids:
        raise ValueError("Retrieval requires at least one lesson ID.")

    relevant_chunks = [
        chunk
        for chunk in load_index(index_path)
        if str(chunk.get("lesson_id")) in lesson_ids
    ]
    if not relevant_chunks:
        raise ValueError("RAG index has no chunks for the requested lessons.")

    query_vector = (embed_fn or clients.embed)(build_query(wrong_questions))
    scored = []
    for chunk in relevant_chunks:
        if "vector" not in chunk or "chunk_text" not in chunk:
            raise ValueError("RAG index chunk is missing required fields.")
        scored.append((cosine_similarity(query_vector, chunk["vector"]), chunk))
    scored.sort(key=lambda item: (-item[0], item[1].get("id", "")))
    return [chunk for _, chunk in scored[:top_k]]
