"""
get_data.py — скрипт для выгрузки данных с Terraria Wiki
Автор: nvclon

Использование:
    python data/get_data.py --mode list     # выгрузить список всех страниц
    python data/get_data.py --mode dump     # выгрузить тексты страниц
    
LICENSE: blablabla
"""

import requests
import json
import time
import os
import argparse

BASE_URL = "https://terraria.wiki.gg/ru/api.php"
HEADERS = {"User-Agent": "TerrariaRAGBot/0.1 (by nvclon)"}

def get_all_pages():
    all_pages = []
    apcontinue = None
    tries = 0

    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "apnamespace": 0,
            "apfilterredir": "nonredirects",
            "aplimit": "500",
            "format": "json",
        }
        if apcontinue:
            params["apcontinue"] = apcontinue

        try:
            r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 429:
                print("⚠️ HTTP 429 Too Many Requests — жду 15 сек...")
                time.sleep(15)
                continue
            if r.status_code != 200:
                print(f"⚠️ HTTP {r.status_code}, жду 10 сек...")
                time.sleep(10)
                continue

            data = r.json()
            if "error" in data:
                print(f"⚠️ Ошибка API: {data['error']['info']}")
                time.sleep(10)
                continue

            if "query" not in data:
                print("⚠️ Нет ключа 'query', повторяю запрос...")
                tries += 1
                if tries > 5:
                    print("❌ Слишком много неудачных попыток — выхожу.")
                    break
                time.sleep(5)
                continue

            pages = data["query"]["allpages"]
            all_pages.extend(pages)
            print(f"✅ Получено страниц: {len(all_pages)}")

            if "continue" in data:
                apcontinue = data["continue"]["apcontinue"]
                time.sleep(1)
            else:
                break

        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            time.sleep(5)

    return all_pages


def dump_page_list():
    os.makedirs("data", exist_ok=True)
    pages = get_all_pages()
    path = "../data/pages_list.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    print(f"💾 Список страниц сохранён в {path} ({len(pages)} штук)")


# ---------------------------------------------
# 2️⃣ Загрузка содержимого страниц
# ---------------------------------------------
def get_page_text(title: str):
    """Получает вики-текст страницы и метаданные"""
    params = {
        "action": "parse",
        "prop": "revisions",
        "rvslots": "main",
        "rvprop": "content|timestamp|user",
        "titles": title,
        "format": "json",
    }

    r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=20)

    if r.status_code == 429:
        print("⚠️ 429 Too Many Requests — жду 20 сек...")
        time.sleep(20)
        return None

    if r.status_code != 200:
        print(f"⚠️ HTTP {r.status_code} при запросе {title}")
        return None

    data = r.json()
    if "query" not in data or "pages" not in data["query"]:
        print(f"⚠️ Нет данных для страницы {title}")
        return None

    page = next(iter(data["query"]["pages"].values()))
    revisions = page.get("revisions", [])
    if not revisions:
        return None

    rev = revisions[0]
    slots = rev.get("slots", {})
    main = slots.get("main", {})

    text = main.get("*", "")
    return {
        "title": title,
        "pageid": page.get("pageid"),
        "ns": page.get("ns"),
        "timestamp": rev.get("timestamp"),
        "user": rev.get("user"),
        "content": text,
    }


def dump_all_pages():
    os.makedirs("data", exist_ok=True)

    # Загружаем список страниц
    if not os.path.exists("../data/pages_list.json"):
        print("❌ Не найден ../data/pages_list.json. Сначала запусти --mode list")
        return

    with open("../data/pages_list.json", "r", encoding="utf-8") as f:
        pages = json.load(f)

    # Загружаем уже скачанные (если есть)
    dump_path = "../data/wiki_dump.json"
    if os.path.exists(dump_path):
        with open(dump_path, "r", encoding="utf-8") as f:
            all_data = json.load(f)
        print(f"🔁 Возобновляем загрузку, уже скачано {len(all_data)} страниц.")
    else:
        all_data = {}

    for i, page in enumerate(pages, start=1):
        title = page["title"]
        if title in all_data:
            continue  # уже скачано

        text = get_page_text(title)
        if text is None:
            continue

        all_data[title] = text
        print(f"{i}/{len(pages)}: {title}")

        # Автосейв каждые 100 страниц
        if i % 100 == 0:
            with open(dump_path, "w", encoding="utf-8") as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            print(f"💾 Автосохранение: {len(all_data)} страниц")

        time.sleep(2)  # небольшая пауза, чтобы не словить 429

    # Финальное сохранение
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Готово! Сохранено {len(all_data)} страниц в {dump_path}")


# ---------------------------------------------
# 3️⃣ CLI
# ---------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Выгрузка Terraria Wiki данных")
    parser.add_argument("--mode", choices=["list", "dump"], required=True, help="Режим: list или dump")
    args = parser.parse_args()

    if args.mode == "list":
        dump_page_list()
    elif args.mode == "dump":
        dump_all_pages()