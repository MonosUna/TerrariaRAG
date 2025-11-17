import os
from dotenv import load_dotenv
from typing import Any

import logging

logger = logging.getLogger('RAG_TerrariaRAG')


CRAFT_AGENT_DESCRIPTION = (
    "CraftAgent - эксперт по крафту предметов в Terraria. "
    "Идеально отвечает на вопросы о рецептах создания предметов, необходимых материалах и инструментах. "
    "Ответственен за любые вопросы связанные с крафтом в игре Terraria."
)

GENERAL_AGENT_DESCRIPTION = (
    "GeneralAgent - универсальный агент по общим вопросам Terraria. "
    "Отвечает на вопросы о механиках игры, биомах, врагах, "
    "NPC, событиях и других аспектах игры. "
    "Ответственен за общие вопросы по игре Terraria."
    "Если вопрос не покрывается специализацией других агентов, GeneralAgent обязательно должен попытаться на него ответить."
)


class TerrariaRAG:

    QUESTION_EXAMPLE = """
    Привет! Расскажи о грани ночи. 
    Какие материалы нужны для его крафта и как он используется в игре?
    """

    REDIRECT_TO_AGENTS_ANSWER_EXAMPLE = """
    {
        "agents": [
            {
                "name": "CraftAgent",
                "reformulated_question": "Как создать грань ночи?"
            },
            {
                "name": "GeneralAgent",
                "reformulated_question": "Что такое грань ночи и как она работает в Terraria?"
            }
        ]
    }
    """

    AGENTS_RESPONSES_EXAMPLE = """
    [
        {
            "Query": "Привет! Расскажи о грани ночи. Какие материалы нужны для его крафта и как он используется в игре?"
        },
        {
            "CraftAgent": "Для создания грани ночи требуется следующие материалы: меч Бич света или Кровавый Забиватель, Мурамаса, Травяной клинок и меч Вулкан. Крафт происходит на демоническом или багровом алтаре.",
        },
        {
            "GeneralAgent": "Грань ночи - это меч, который создаётся из хлорофитовых слитков. При использовании, меч испускает фиолетовые частицы, напоминающие частицы теневых предметов. Используется в качестве основного оружия ближнего боя в поздней игре Terraria."
        }
    ]
    """

    MERGED_ANSWER_EXAMPLE = """
    Привет! Сейчас расскажу. Грань ночи - это мощное оружие ближнего боя, которое особенно эффективно в поздней игре Terraria.
    Он крафтится на демоническом или багровом алтаре из четырёх уникальных мечей: Бич света или Кровавый Забиватель, Мурамаса, Травяной клинок и меч Вулкан.
    При использовании, меч испускает фиолетовые частицы, напоминающие частицы теневых предметов.
    """

    # Промпты для подготовки вопросов к агентам и объединения ответов

    SYSTEM_PROMPT__REDIRECT_TO_AGENTS = """
    Ты — интеллектуальный ассистент по игре Terraria.
    Пользователь задаёт вопрос, связанный с разными аспектами игры.

    Твоя задача - определить, каких агентов нужно привлечь для ответа на вопрос
    и переформулировать вопрос для каждого агента с учётом его специализации.

    Инструкция:
    1. Проанализируй вопрос пользователя.
    2. Определи, какие агенты могут помочь ответить на вопрос.
    3. Для каждого выбранного агента переформулируй вопрос так,
       чтобы он соответствовал специализации агента.
    4. Верни результат в формате JSON
    5. Если ни один агент не подходит, верни пустой список агентов.
    6. Для каждого крафта должен быть отдельный запрос к CraftAgent!

    Доступные агенты:
    
    1. Имя: CraftAgent. Описание: {CRAFT_AGENT_DESCRIPTION}
       Для CraftAgent переформулированный вопрос должен содержать только названия предметов, которые связаны с крафтом.
    2. Имя: GeneralAgent. Описание: {GENERAL_AGENT_DESCRIPTION}
       GeneralAgent должен получать вопросы, которые не покрываются специализацией других агентов.

    Пример запроса:
    {QUESTION_EXAMPLE}
    
    Пример ответа:
    {REDIRECT_TO_AGENTS_ANSWER_EXAMPLE}

    Для каждого агента укажи:
    - name: имя агента
    - reformulated_question: переформулированный вопрос для данного агента
    Ответ обязан быть в точности таком формате:

    {
        "agents": [
            {
                "name": "NameOfAgent",
                "reformulated_question": "..."
            },
            {
                "name": "PossiblyOtherNameOfAgent",
                "reformulated_question": "..."
            },
            ...
        ]
    }
    
    """

    SYSTEM_PROMPT__SUMMARIZE_ANSWERS = """
    Ты — интеллектуальный ассистент по игре Terraria.
    Пользователь задал вопрос, на части которого ответили несколько специализированных агентов.

    Вот их описание:
    1. Имя: CraftAgent. Описание: {CRAFT_AGENT_DESCRIPTION}
    2. Имя: GeneralAgent. Описание: {GENERAL_AGENT_DESCRIPTION}

    Твоя задача:
    1. Прочитать ответы агентов
    2. Сформулировать единый, полный и связный ответ на исходный вопрос пользователя
    3. Учесть специализацию каждого агента при формировании ответа
    4. Если тебе хватает способностей информативно дополнить ответ, не давая ложной информации, сделай это.
    5. Не упоминай ничего об агентах — просто предоставь итоговый ответ пользователю, основанный на предоставленной информации.
    
    Пример вопроса пользователя:
    {QUESTION_EXAMPLE}

    Входные данные, которые ты получил от агентов, вместе с исходным вопросом пользователя:
    {AGENTS_RESPONSES_EXAMPLE}
    Обрати внимание, что первый элемент - это исходный вопрос пользователя.

    Пример итогового ответа:
    {MERGED_ANSWER_EXAMPLE}
    """

    def __init__(
            self,
            llm_session: Any,
            agents: list,
            ):
        self.llm_session = llm_session
        self.agents = agents
        self.message_history = []
        self.set_api_key()
        
    def set_temperature(self, temperature):
        if not (0.0 <= temperature <= 1.0):
            raise ValueError("Temperature must be between 0.0 and 1.0")
        self.temperature = temperature
        
    def set_api_key(self):
        load_dotenv()
        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY not found in environment variables.")
    
    def _get_reformulated_questions(self, query):
        """
        Получает переформулированные вопросы для каждого агента.
        """
        system_prompt = self.SYSTEM_PROMPT__REDIRECT_TO_AGENTS
        user_prompt = "Запрос пользователя: {query}".format(query=query)
        
        response = self.llm_session.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # Парсинг ответа для получения списка агентов и вопросов

        start = response.find('{')
        end = response.rfind('}')

        if start != -1 and end != -1 and end > start:
            response = response[start:end+1]

        import json
        try:
            agent_requests = json.loads(response).get("agents", [])
        except json.JSONDecodeError:
            agent_requests = []

        if agent_requests == []:
            agent_requests = [
                {
                    "name": "GeneralAgent",
                    "reformulated_question": query
                }
            ]
        
        return agent_requests

    def _get_agents_responses(self, agent_requests):
        """
        Получает ответы от всех агентов на переформулированные вопросы.
        """
        agent_responses = []
        
        # Шаг 2: Вызов каждого агента с переформулированным вопросом
        for agent_request in agent_requests:
            agent_name = agent_request["name"]
            reformulated_question = agent_request["reformulated_question"]
            
            # Поиск агента по имени
            agent = next((a for a in self.agents if a.name == agent_name), None)
            if agent:
                agent_response_raw, _ = agent.call(reformulated_question)
                agent_response = {
                    agent_name: agent_response_raw
                }
                agent_responses.append(agent_response)

        
        return agent_responses
    
    def _build_final_answer(self, agents_responses):
        """
        Строит окончательный ответ на основе ответов агентов.
        Учитывает специализацию каждого агента.
        """
        system_prompt = self.SYSTEM_PROMPT__SUMMARIZE_ANSWERS
        user_prompt = "Входные данные: {responses}".format(responses=agents_responses)

        final_answer = self.llm_session.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        return final_answer
    
    def run(self, query: str) -> str:
        """
        Основной метод для генерации ответа на пользовательский запрос.
        """
        logger.info(f"Запрос пользователя: \n{query}\n" + "=" * 50)
        agent_requests = self._get_reformulated_questions(query)
        logger.info(f"Переформулированные вопросы агентам: \n{agent_requests}\n" + "=" * 40)
        agents_responses = self._get_agents_responses(agent_requests)
        agents_responses_with_query = [{"Query": query}] + agents_responses
        logger.info(f"Ответы агентов: ")
        for response in agents_responses_with_query:
            if response.get("Query") is not None:
                continue
            for agent_name, answer in response.items():
                logger.info(f"{agent_name} ответил: \n{answer}\n")
        final_answer = self._build_final_answer(agents_responses_with_query)
        return final_answer
