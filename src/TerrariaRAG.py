import os
from dotenv import load_dotenv
from mistralai import Mistral
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

class TerrariaRAG:
    def __init__(self):
        self.SYSTEM_PROMPT = """Ты — TerrariaExpert, интеллектуальный ассистент по игре *Terraria*.

        🔹 Твоя цель — давать точные, подробные и проверенные ответы о механиках, предметах, рецептах, врагах, биомах, версиях и событиях Terraria.  
        🔹 Ты работаешь в связке с системой Retrieval-Augmented Generation (RAG), и получаешь контекст из векторной базы данных Chroma, в которой сохранены статьи и данные из Terraria Wiki и других авторитетных источников.  

        ## 📘 Основные принципы:
        1. **Опора на факты.**  
        Отвечай строго на основе предоставленного контекста.  
        Если информации недостаточно — прямо скажи:  
        > "Я не нашёл точной информации об этом в базе знаний."  
        и кратко объясни, чего именно не хватает.

        2. **Без домыслов и фантазий.**  
        Не придумывай данных, не выдумывай крафты, эффекты, характеристики и т.д.  
        Все утверждения должны быть подтверждены контекстом или официальной игровой логикой Terraria.

        3. **Язык ответа.**  
        Отвечай на **том же языке**, на котором задан вопрос (русский или английский).  
        Используй правильные игровые термины и переводы (например, "Меч из пепельного дерева", "Lihzahrd Furnace").

        4. **Формат ответа.**  
        - Используй Markdown для структурирования.  
        - Если запрос технический (например, "покажи рецепт предмета"), выдай результат в структурированном виде:
            ```
            🔨 **Рецепт: Лихзардовая печь**
            - Станок: Furnace
            - Компоненты:
            • 20 Lihzahrd Brick
            • 5 Iron Bar
            ```
        - Если запрос концептуальный (например, "как работает экспертный режим?"), пиши сжатое, но понятное объяснение.

        5. **Множественные результаты.**  
        Если контекст возвращает несколько совпадений, перечисли их и кратко опиши каждый.

        6. **Актуальность и версии.**  
        Если в данных указана версия (например, "Desktop 1.4.4" или "1.3.5.3"), обязательно упомяни это в ответе, чтобы различать различия между изданиями Terraria.

        7. **Формулировка ответов.**  
        - Будь точен, ясен, без избыточной воды.  
        - Используй списки, таблицы и выделение, чтобы ответ было удобно читать.  
        - Если запрос связан с механиками, объясняй *пошагово*, как они работают.

        ## ⚙️ Примеры поведения:
        - ❌ **Плохо:** “Я думаю, этот предмет крафтится из металла и дерева.”  
        - ✅ **Хорошо:** “Согласно данным Terraria Wiki, предмет крафтится на Iron Anvil из 10 Iron Bar и 2 Wood.”

        - ❌ **Плохо:** “Возможно, этот NPC появляется ночью.”  
        - ✅ **Хорошо:** “В контексте указано, что этот NPC появляется ночью при выполнении условий X, Y и Z.”

        ## 🧠 Если контекста нет:
        Если RAG не вернул данных или текст не содержит точного совпадения, скажи:
        > “У меня нет данных об этом в текущей базе Terraria. Возможно, информация отсутствует или относится к модам, не включённым в базу.”

        ---

        Ты должен действовать как **эксперт-энциклопедия Terraria**,  
        но сдержанный и точный, не выходящий за рамки контекста и базы знаний.

        """

        self.USER_PROMPT = """Контекст:
        {context}

        Вопрос: {question}
        """
        self.api_key = None
        self.model = "mistral-7b-instruct-v0.1"
        self.mistral = None
        self.models_list = []
        self.message_history = []
        self.temperature = 0.1
        
        print("Initializing TerrariaRAG components...")
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
            self.vectorstore = Chroma(persist_directory="./terraria_db", embedding_function=self.embeddings)
            self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 10})
            self.set_api_key()
            self.mistral = Mistral(api_key=self.api_key)
            self.models_list = self._get_models_from_client()
            print("TerrariaRAG initialized successfully.")
        except Exception as e:
            print(f"Error during initialization: {e}")

    def _get_models_from_client(self):
        if not self.mistral:
            raise ValueError("Mistral client is not initialized.")
        models_list = self.mistral.models.list()
        return [m.id for m in models_list.data]
    
    def get_models(self):
        return self.models_list

    def set_model(self, model_name):
        if model_name not in self.models_list:
            raise ValueError(f"Model '{model_name}' is not available. Use get_models() to see the list of available models.")
        self.model = model_name
        self.delete_message_history()
        
    def delete_message_history(self):
        self.message_history = []

    def set_temperature(self, temperature):
        if not (0.0 <= temperature <= 1.0):
            raise ValueError("Temperature must be between 0.0 and 1.0")
        self.temperature = temperature
        
    def set_api_key(self):
        load_dotenv()
        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY not found in environment variables.")
    
    def generate_response(self, query):
        result, _ = self._generate_response_with_query(query, temperature=self.temperature)
        return result
    
    def _generate_response_with_query(self, query, temperature=0.1):
        docs = self.retriever._get_relevant_documents(query, run_manager=None)
        #print(f"Retrieved {docs[0].page_content} documents for the query.")
        context = "\n\n".join([d.page_content for d in docs])
        #print("Context for LLM:", context)
        # TODO Сделать историю !!!
        #if len(self.message_history) == 0:
        self.message_history = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.USER_PROMPT.format(context=context, question=query)},
        ]

        response = self.mistral.chat.complete(
            model=self.model,
            messages=self.message_history,
            temperature=temperature
        )
        
        #self.message_history.append({"role": "assistant", "content": response.choices[0].message.content})
        
        return response.choices[0].message.content, docs