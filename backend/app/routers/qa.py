from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from app.schemas import AskRequest, AskResponse
from app.services import qa
from app.services.embeddings import EmbeddingError

router = APIRouter(tags=["qa"])


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    try:
        result = qa.answer_question(
            request.question.strip(), document_ids=request.document_ids, top_k=request.top_k
        )
    except (EmbeddingError, qa.AnswerGenerationError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return AskResponse(answer=result.answer, sources=[asdict(hit) for hit in result.sources])
