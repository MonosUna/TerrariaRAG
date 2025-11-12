import json
import os
import re


def replace_wikilinks(text: str) -> str:
    """Заменяет все [[...]] на последнюю часть после |"""
    def repl(match):
        inner = match.group(1)
        return inner.split("|")[-1].strip()

    return re.sub(r"\[\[([^\[\]]+)\]\]", repl, text)


def remove_templates(text: str) -> str:
    """Удаляет все шаблоны {{...}} включая вложенные"""
    pattern = re.compile(r"\{\{[^{}]*\}\}")
    while re.search(pattern, text):
        text = re.sub(pattern, "", text)
    return text


def remove_wiki_tags(text: str) -> str:
    """Удаляет <noinclude>...</noinclude> и подобные wiki-теги"""
    text = re.sub(r"<noinclude>.*?</noinclude>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<includeonly>.*?</includeonly>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<onlyinclude>.*?</onlyinclude>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text


def clean_entry(entry: dict) -> dict:
    """Очищает поле 'content'"""
    content = entry.get("content", "")
    if not content:
        return entry

    content = replace_wikilinks(content)
    content = remove_templates(content)
    content = remove_wiki_tags(content)

    # Убираем лишние пробелы и пустые строки
    content = re.sub(r"\n\s*\n+", "\n", content)
    content = re.sub(r"[ \t]{2,}", " ", content)
    content = content.strip()

    entry["content"] = content
    return entry


def clean_all(file_path="wiki_dump_raw.json", output_path="wiki_dump_test_without_temps.json"):
    """Очищает все записи и сохраняет обратно"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    with open(file_path, "r", encoding="utf-8") as infile:
        data = json.load(infile)

    cleaned_data = [clean_entry(data[entry]) for entry in data]

    with open(output_path, "w", encoding="utf-8") as outfile:
        json.dump(cleaned_data, outfile, ensure_ascii=False, indent=4)

    print(f"✅ Cleaned data written to {output_path}. Total entries: {len(cleaned_data)}")


if __name__ == "__main__":
    clean_all()
