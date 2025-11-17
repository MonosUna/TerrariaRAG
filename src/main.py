import logging
from TerrariaRAG import TerrariaRAG

from agent import MistralLLM, CraftAgent, GeneralAgent
from mistralai import Mistral
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from logging_config import setup_logging

import os
import json
import warnings


warnings.filterwarnings("ignore")

logger = logging.getLogger('RAG_main')

load_dotenv()

def setup_terraria_rag() -> TerrariaRAG:
    logger.info("Загрузка TerrariaRAG...")
    logger.info("Инициализация LLM клиента...")

    client = MistralLLM(
        mistral_client=Mistral(
            api_key=os.getenv("API_KEY"),
        ),
        model_name="mistral-small-latest",
    )

    logger.info("LLM клиент инициализирован.")
    logger.info("Загрузка вспомогательных данных...")

    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large"
    )
    recipes = json.load(open("data/recipes.json", "r", encoding="utf-8"))

    logger.info("Вспомогательные данные загружены.")
    logger.info("Создание агентов...")

    craft_agent = CraftAgent(
        name="CraftAgent",
        llm_session=client,
        recipes=recipes,
        embeddings=embeddings,
        max_recipes=24
    )

    general_agent = GeneralAgent(
        name="GeneralAgent",
        llm_session=client,
        embeddings=embeddings,
        max_docs=8
    )

    logger.info("Агенты созданы.")
    logger.info("Создание TerrariaRAG...")

    terraria_rag = TerrariaRAG(
        llm_session=client,
        agents=[
            craft_agent, 
            general_agent
        ]
    )

    logger.info("TerrariaRAG создан.")

    return terraria_rag


if __name__ == "__main__":
    setup_logging()
    question = input("Введите ваш вопрос по Terraria: ")
    if question.strip() == "":
        question = (
            "Что такое молниеносные ботинки, зачем они нужны и как их создать? "
            "А ещё как получить искромётные морозные ботинки?"
        )
    
    terraria_rag = setup_terraria_rag()
    response = terraria_rag.run(question)
    print("=" * 70)
    print("Вопрос:", question, "\n")
    print("Ответ:", response)



"""

Сколько в среднем скелетов нужно убить, чтобы скрафтить полный сет некроброни?

Сколько нужно хлорофитовых слитков для создания полного сета хлорофитовой брони и какие предметы входят в этот сет? А ещё, как разблокировать хлорофит в игре Terraria?

Я очень хочу получить эмблему мстителя! Как мне её скрафтить и как я могу использовать её?

Нужно ли мне ночью спать в Террарии, чтобы спастить от зомби? Как скрафтить кровать и сколько разных кроватей есть в игре?

"""
