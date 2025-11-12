import json
import os
import re


def replace_wikilinks(text: str) -> str:
    """Заменяет все [[...]] на последнюю часть после |"""
    def repl(match):
        inner = match.group(1)
        return inner.split("|")[-1].strip()

    return re.sub(r"\[\[([^\[\]]+)\]\]", repl, text)


def clean_entry(entry: dict) -> dict:
    """Очищает поле 'content'"""
    content = entry.get("content", "")
    if not content:
        return entry

    entry["content"] = replace_wikilinks(content)
    return entry


def clean_all(file_path="wiki_dump_raw.json", output_path="wiki_dump_clean.json"):
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
