import os
import json
import logging
import time
from dotenv import load_dotenv
from mistralai import Mistral
import sys

load_dotenv()
logger = logging.getLogger("CalculateMetrics")
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

SRC_DIR = os.path.join(ROOT_DIR, 'src')
sys.path.insert(0, SRC_DIR)

from src.main import setup_terraria_rag
from src.agent import MistralLLM


#############################################
# 0 — Retry Helpers
#############################################

def safe_eval_call(client, q, gt, my_answer, baseline_answer):
    """
    Делает повторные запросы к API, пока не получим успешный ответ.
    """
    while True:
        try:
            return evaluate_answer(client, q, gt, my_answer, baseline_answer)
        except Exception as e:
            logger.warning(f"Baseline error: {e}, retrying in 30s...")
            time.sleep(30)


def safe_run_rag(rag, question):
    """
    Делает повторные запросы к API, пока не получим успешный ответ.
    """
    while True:
        try:
            return rag.run(question)
        except Exception as e:
            logger.warning(f"RAG error: {e}, retrying in 30s...")
            time.sleep(30)


def safe_baseline_answer(baseline, question):
    """
    Делает повторные запросы к API, пока не получим успешный ответ.
    """
    while True:
        try:
            return baseline.call(system_prompt="Ты эксперт по игре Terraria. Ответь на вопрос: ", user_prompt=question)
        except Exception as e:
            logger.warning(f"Baseline error: {e}, retrying in 30s...")
            time.sleep(30)


#############################################
# 1 — Оценщик (большая LLM-модель)
#############################################
def evaluate_answer(eval_client, question, groundtruth, my_answer, baseline_answer):
    """
    Оценивает ответы модели и baseline с помощью LLM, используя метод .call().
    """
    system_prompt = """
Ты — строгий оценщик ответов на вопросы по Terraria.
Сравни два ответа на один вопрос с точки зрения качества и соответствия groundtruth.
Сильно наказывай ложь со стороны модели.
Если ответ модели содержит дополнительную информацию, то не наказывай модель.
Вот примерные критерии.
0 - ответ полностью неверен.
1 - ответ верен лишь немного
2 - ответ частично верен, но содержит галлюцинации.
3 - почти полностью верен, но не полон.
4 - ответ верен, но возможно не совсем полон.
5 - ответ полностью верен и полон.
Верни JSON строго в формате:

{
    "rag_score": int,      # 0–5
    "baseline_score": int  # 0–5
}
"""

    user_prompt = f"""
Question: {question}

Groundtruth:
{groundtruth}

--- My Model Answer ---
{my_answer}

--- Baseline Answer ---
{baseline_answer}
"""

    # Вызов LLM через .call()
    response = eval_client.call(system_prompt=system_prompt, user_prompt=user_prompt)

    text = response  # call() возвращает текст напрямую

    # Извлекаем JSON из текста
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Evaluator returned non-JSON result")

    json_text = text[start:end+1]
    return json.loads(json_text)


#############################################
# 2 — Основной цикл
#############################################

def calculate_metrics():
    logging.basicConfig(level=logging.INFO)
    logger.info("Загружаем бенчмарк...")
    with open("metrics/benchmark_questions.json", "r", encoding="utf-8") as f:
        questions = json.load(f)

    logger.info("Инициализация TerrariaRAG...")
    terraria_rag = setup_terraria_rag()

    logger.info("Инициализация baseline модели...")
    baseline = MistralLLM(
        mistral_client=Mistral(
            api_key=os.getenv("API_KEY"),
        ),
        model_name="ministral-8b-2410",
    )

    logger.info("Инициализация модели-оценщика...")
    eval_client = MistralLLM(
        mistral_client=Mistral(
            api_key=os.getenv("API_KEY"),
        ),
        model_name="ministral-8b-2410",
    )

    # Загружаем предыдущие результаты, если они есть
    results = load_existing_results()

    # Получаем список уже обработанных вопросов
    processed_questions = {r["question"] for r in results}

    for i, item in enumerate(questions):
        q = item["question"]
        theme = item.get("theme", "")
        gt = item["groundtruth"]

        # Пропускаем уже обработанные вопросы
        if q in processed_questions:
            logger.info(f"Пропускаем уже обработанный вопрос: {q}")
            continue

        logger.info(f"Обработка ({i+1}/{len(questions)}): {q}")

        try:
            my_answer = safe_run_rag(terraria_rag, q)
        except Exception as e:
            logger.error(f"My model error: {e}")
            my_answer = ""

        try:
            baseline_answer = safe_baseline_answer(baseline, q)
        except Exception as e:
            logger.error(f"Baseline error: {e}")
            baseline_answer = ""

        try:
            eval_result = safe_eval_call(
                eval_client, q, gt, my_answer, baseline_answer
            )
        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            eval_result = {
                "rag_score": 0,
                "baseline_score": 0
            }

        # Добавляем новый результат
        new_result = {
            "question": q,
            "theme": theme,
            "groundtruth": gt,
            "my_model_answer": my_answer,
            "baseline_answer": baseline_answer,
            "evaluation": eval_result
        }
        results.append(new_result)

        # Сохраняем после каждого вопроса
        save_results(results)
        logger.info(f"Сохранен результат для вопроса {i+1}/{len(questions)}")

    logger.info("🎉 Все метрики вычислены! Финальный результат в metrics/out/model_evaluation.json")

def load_existing_results():
    """Загружает существующие результаты если они есть"""
    os.makedirs("metrics/out", exist_ok=True)
    results_file = "metrics/out/model_evaluation.json"

    if os.path.exists(results_file):
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                results = json.load(f)
            logger.info(f"Загружено {len(results)} предыдущих результатов")
            return results
        except Exception as e:
            logger.warning(f"Не удалось загрузить предыдущие результаты: {e}")

    return []

def save_results(results):
    """Сохраняет результаты в файл"""
    os.makedirs("metrics/out", exist_ok=True)
    results_file = "metrics/out/model_evaluation.json"

    try:
        temp_file = results_file + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        os.replace(temp_file, results_file)
        logger.debug(f"Результаты сохранены ({len(results)} записей)")

    except Exception as e:
        logger.error(f"Ошибка сохранения результатов: {e}")

if __name__ == "__main__":
    calculate_metrics()
