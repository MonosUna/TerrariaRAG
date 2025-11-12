import requests
from bs4 import BeautifulSoup

BASE_URL = "https://terraria.wiki.gg/ru/api.php"

def get_parsed_text(title: str):
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
    }

    r = requests.get(BASE_URL, params=params, timeout=20)
    r.raise_for_status()  # бросит исключение при ошибке HTTP

    data = r.json()

    # Проверяем, есть ли ключ "parse"
    if "parse" not in data:
        print("⚠️ Не удалось получить parse для", title)
        print(data)
        return None

    html = data["parse"]["text"]["*"]

    # Очищаем HTML до обычного текста
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")

    return text.strip()


if __name__ == "__main__":
    title = "Рецепты/Ящщеровая печь/register"  # или "1.0.1" для теста
    text = get_parsed_text(title)
    print(text[:2000])  # печатаем первые 2000 символов
