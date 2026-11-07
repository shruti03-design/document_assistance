"""Question answering grounded in retrieved document chunks (the "G" in RAG)."""
from dataclasses import dataclass

import openai

from app.config import settings
from app.services import embeddings, vector_store
from app.services.vector_store import SearchHit

NO_CONTEXT_ANSWER = (
    "I couldn't find any relevant information in your documents. "
    "Try uploading a document first, or rephrase your question."
)

SYSTEM_PROMPT = """You are a document assistant. Answer the user's question using ONLY the \
numbered context passages provided from their documents.

Rules:
- Base every statement on the context. Do not use outside knowledge or make assumptions.
- If the context does not contain the answer, say: "I don't know based on the provided \
documents." You may briefly mention what the documents do cover.
- Cite the passages you used with their numbers in square brackets, e.g. [1] or [2][3].
- Be concise and direct."""


class AnswerGenerationError(Exception):
    pass


@dataclass
class Answer:
    answer: str
    sources: list[SearchHit]


def build_context(hits: list[SearchHit]) -> str:
    return "\n\n".join(
        f"[{i}] (document: {hit.document_name}, page {hit.page_number})\n{hit.text}"
        for i, hit in enumerate(hits, start=1)
    )


def build_messages(question: str, hits: list[SearchHit]) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Context:\n{build_context(hits)}\n\nQuestion: {question}",
        },
    ]


def generate_answer(messages: list[dict]) -> str:
    try:
        response = embeddings.get_client().chat.completions.create(
            model=settings.chat_model,
            messages=messages,
        )
    except openai.OpenAIError as exc:
        raise AnswerGenerationError(f"Answer generation failed: {exc}") from exc
    return (response.choices[0].message.content or "").strip()


def answer_question(
    question: str, document_ids: list[int] | None = None, top_k: int | None = None
) -> Answer:
    query_vector = embeddings.embed_query(question)
    hits = vector_store.search(
        query_vector, limit=top_k or settings.retrieval_top_k, document_ids=document_ids
    )
    if not hits:
        # Nothing to ground an answer in, so don't ask the LLM at all
        return Answer(answer=NO_CONTEXT_ANSWER, sources=[])

    return Answer(answer=generate_answer(build_messages(question, hits)), sources=hits)
