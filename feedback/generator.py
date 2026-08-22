"""End-to-end retrieval-augmented feedback generation."""

from feedback.clients import generate_text
from feedback.prompts import SYSTEM_PROMPT, build_prompt
from feedback.retriever import retrieve


def generate_feedback(*, session_result, wrong_items, lesson_ids):
    """Generate 3-5 sentence feedback, retrieving only when answers were wrong."""
    retrieved_chunks = (
        retrieve(lesson_ids, wrong_items, top_k=4) if wrong_items else []
    )
    prompt = build_prompt(session_result, wrong_items, retrieved_chunks)
    return generate_text(system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
