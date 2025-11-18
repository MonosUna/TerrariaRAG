from typing import Any, Dict, List, Optional
from langchain_community.vectorstores import Chroma

import abc
import logging


logger = logging.getLogger('RAG_Agent')

class MistralLLM:
    """
    Обертка для клиента Mistral.
    Сохраняет настройки модели, температуру и историю запросов.
    """

    def __init__(
            self, 
            mistral_client: Any, 
            model_name: str = "mistral-small-latest", 
            temperature: float = 0.2):
        
        self.client = mistral_client
        self.model_name = model_name
        self.temperature = temperature

    def call(self, system_prompt: str, user_prompt: str) -> str:
        """
        Вызывает клиент Mistral и возвращает текст ответа модели.
        """
        if not self.client:
            raise ValueError("Mistral client is not set on MistralLLM")

        messages = [
            {"role": "system", "content": system_prompt}, 
            {"role": "user", "content": user_prompt}
        ]
        resp = self.client.chat.complete(
            model=self.model_name, 
            messages=messages, 
            temperature=self.temperature
        )
        try:
            return resp.choices[0].message.content
        except Exception:
            try:
                return str(resp)
            except Exception:
                raise


class Agent(abc.ABC):
    """
    Абстрактный класс для Агента
    """

    def __init__(self, name: str, llm_session: Any):
        self.name = name
        self.llm_session = llm_session

    @abc.abstractmethod
    def call(self, query: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()


class CraftAgent(Agent):
    """
    Специализированный агент, который умеет создавать ответы, 
    связанные с крафтом предметов.
    """

    SYSTEM_PROMPT = (
        "Ты помощник по игре Terraria. Твоя задача - помогать игрокам "
        "находить рецепты крафта предметов на основе предоставленной информации. "
        "Для каждого запрошенного предмета ты должен предоставить все возможные рецепты крафта. "
        "Если рецепты для запрошенного предмета не найдены, честно скажи об этом."
    )

    USER_PROMPT = (
        "Информация о рецептах крафтов:\n{context}\n"
        "Ответь на запрос: {query}"
    )

    def __init__(
            self, 
            name: str,
            llm_session: Any, 
            recipes: Any,
            embeddings: Optional[Any] = None,
            max_recipes: int = 5
            ):
        super().__init__(name, llm_session)
        self.recipes = recipes
        self.max_recipes = max_recipes
        self.embeddings = embeddings
        self.vectorstore = Chroma(persist_directory="./terraria_db/recipes", embedding_function=self.embeddings)
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": self.max_recipes})
    
    def _get_recipes_context(self, item_names: List[str]) -> str:
        contexts = []
        for item in item_names:
            if not self.recipes.get(item, {}).get("recipes"):
                contexts.append(f"Рецепты для {item} не найдены.\n")
                continue

            context = ""
            for recipe in self.recipes.get(item, {}).get("recipes", []):
                components = ", ".join([f"{comp} x{qty}" for comp, qty in recipe["components"].items()])
                if not recipe.get("station"):
                    station = "Без верстака"
                else:
                    station = recipe["station"]
                context += f"- Станция: {station}, Компоненты: {components}\n"
            
            contexts.append(f"Рецепты для {item}:\n{context}\n")

        return "\n".join(contexts) if contexts else "Рецепты не найдены."

    def call(self, query: str) -> Dict[str, Any]:
        """
        Поведение:
        - Достаёт из Chroma DB k наиболее подходящих названий предметов для крафта
        - В предоставленом контексте достаёт информацию о крафте этих предметов
        - Полученные рецепты передаёт в пропмт LLM для генерации ответа
        """

        docs = self.retriever._get_relevant_documents(query, run_manager=None)
        item_names = "\n".join([d.page_content for d in docs])

        context = self._get_recipes_context(item_names.split("\n"))
        # logger.info(f"CraftAgent контекст для запроса '{query}': \n{context}\n")

        response_text = self.llm_session.call(
            system_prompt=CraftAgent.SYSTEM_PROMPT,
            user_prompt=CraftAgent.USER_PROMPT.format(context=context, query=query)
        )
        return response_text, docs


class GeneralAgent(Agent):
    """
    Общий агент, который умеет отвечать на общие вопросы по игре
    """

    SYSTEM_PROMPT = (
        "Ты помощник по игре Terraria. "
        "Ты владеешь только информацией, которая содержится в предоставленных документах. "
        "Тебе нельзя врать или придумывать информацию. "
        "Если информации недостаточно, скажи, что не знаешь подробностей. "
    )

    USER_PROMPT = (
        "Используя следующие документы:\n{context}\n"
        "Ответь на запрос: {query}"
    )

    def __init__(
            self, 
            name: str,
            llm_session: Any, 
            embeddings: Optional[Any] = None,
            max_docs: int = 5
            ):
        super().__init__(name, llm_session)
        self.max_docs = max_docs
        self.embeddings = embeddings
        self.vectorstore = Chroma(persist_directory="./terraria_db/general", embedding_function=self.embeddings)
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": self.max_docs})

    def call(self, query: str) -> Dict[str, Any]:
        """
        Поведение:
        - Достаёт из Chroma DB k наиболее релевантных документов
        - Передаёт эти документы в пропмт LLM для генерации ответа
        """
        docs = self.retriever._get_relevant_documents(query, run_manager=None)

        context = "\n".join([d.page_content for d in docs]) if docs else "Документы не найдены."
        # logger.info(f"GeneralAgent контекст для запроса '{query}': \n{context}\n")

        response_text = self.llm_session.call(
            system_prompt=GeneralAgent.SYSTEM_PROMPT,
            user_prompt=GeneralAgent.USER_PROMPT.format(context=context, query=query)
        )
        return response_text, docs


__all__ = ["MistralLLM", "Agent", "CraftAgent", "GeneralAgent"]
