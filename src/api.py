import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from .logging_config import setup_logging
from .main import setup_terraria_rag


logger = logging.getLogger("RAG_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan-хэндлер для инициализации TerrariaRAG при запуске приложения.
    """
    setup_logging()
    app.state.terraria_rag = setup_terraria_rag()
    yield


app = FastAPI(title="Terraria RAG API", lifespan=lifespan)


@app.get("/ask")
def ask(question: str, request: Request) -> str:
    """
    HTTP-эндпоинт для обращения к RAG-системе.
    Принимает строковый параметр `question` и возвращает строковый ответ.
    """
    terraria_rag = getattr(request.app.state, "terraria_rag", None)
    if terraria_rag is None:
        raise HTTPException(status_code=503, detail="RAG система ещё не инициализирована")

    if not question.strip():
        raise HTTPException(status_code=400, detail="Параметр 'question' не должен быть пустым")

    return terraria_rag.run(question)
