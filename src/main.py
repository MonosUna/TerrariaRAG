import logging
import json
import warnings

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

try:
    # Импорт при использовании пакета src (например, uvicorn src.api:app)
    from .TerrariaRAG import TerrariaRAG
    from .agent import CraftAgent, GeneralAgent
    from .logging_config import setup_logging
except ImportError:
    # Импорт при прямом запуске файла (python src/main.py)
    from TerrariaRAG import TerrariaRAG
    from agent import CraftAgent, GeneralAgent
    from logging_config import setup_logging


warnings.filterwarnings("ignore")

logger = logging.getLogger('RAG_main')

load_dotenv()

def setup_terraria_rag() -> TerrariaRAG:
    logger.info("Загрузка TerrariaRAG...")
    logger.info("Инициализация LLM клиента...")

    api_url = "http://192.168.68.111:8000/api/generate"

    logger.info("LLM клиент инициализирован.")
    logger.info("Загрузка вспомогательных данных...")

    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large"
    )
    recipes = json.load(open("data/data/recipes.json", "r", encoding="utf-8"))

    logger.info("Вспомогательные данные загружены.")
    logger.info("Создание агентов...")

    craft_agent = CraftAgent(
        name="CraftAgent",
        api_url=api_url,
        recipes=recipes,
        embeddings=embeddings,
        max_recipes=24
    )

    general_agent = GeneralAgent(
        name="GeneralAgent",
        api_url=api_url,
        embeddings=embeddings,
        max_docs=8
    )

    logger.info("Агенты созданы.")
    logger.info("Создание TerrariaRAG...")

    terraria_rag = TerrariaRAG(
        api_url=api_url,
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
            "Какой урон у снайперской винтовки?"
        )
    
    terraria_rag = setup_terraria_rag()
    terraria_rag.set_temperature(0.1)
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
