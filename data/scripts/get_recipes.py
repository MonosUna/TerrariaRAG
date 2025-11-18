import json
import re

def get_all_recipes():
    with open("data/data/wiki_dump_raw.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    recipes = {}

    for key in data:
        out = parse_to_object_format(data[key]['content'])

        for name, info in out.items():
            if name not in recipes:
                recipes[name] = info
            else:
                # ДОБАВЛЯЕМ рецепты, а не перезаписываем предмет
                recipes[name]["recipes"].extend(info["recipes"])

                # ЕСЛИ старого id нет, берем новый
                if recipes[name].get("id") is None and info.get("id") is not None:
                    recipes[name]["id"] = info["id"]

    return recipes

def parse_to_object_format(text):
    # удаляем строки с version, чтобы не мешали вложенные {{...}}
    text = re.sub(r"\|\s*version\s*=.*", "", text, flags=re.I)

    # находим блоки {{recipes/register ...}}
    blocks = re.findall(r"\{\{recipes/register(.*?)\}\}", text, flags=re.S)

    out = {}

    for block in blocks:
        lines = block.strip().split("\n")

        result_name = None
        result_id = None
        result_amount = None
        station = None
        components = {}

        for raw in lines:
            line = raw.strip().lstrip("|").strip()
            if not line:
                continue

            # CASE 1: result с параметрами
            if line.startswith("result"):
                _, val = map(str.strip, line.split("=", 1))
                parts = [p.strip() for p in val.split("|")]
                result_name = parts[0]
                for p in parts[1:]:
                    if "=" in p:
                        k, v = map(str.strip, p.split("=", 1))
                        k = k.lower()
                        if k == "resultid":
                            result_id = int(v)
                        elif k == "amount":
                            result_amount = int(v)
                continue

            # CASE 2: key = value
            if "=" in line:
                key, val = map(str.strip, line.split("=", 1))
                key = key.lower()
                if key == "station":
                    station = [s.strip() for s in re.split(r"\band\b|,|\+|/", val)]
                    station = [s for s in station if s]
                elif key == "resultid":
                    result_id = int(val)
                elif key == "amount":
                    result_amount = int(val)
                continue

            # CASE 3: ингредиенты
            if "|" in line:
                ing_name, qty = map(str.strip, line.split("|", 1))
                if qty.isdigit():
                    components[ing_name] = int(qty)

        if station and len(station) == 1:
            station = station[0]

        if result_name:
            out[result_name] = {
                "id": result_id,
                "recipes": [
                    {
                        "components": components,
                        "amount": result_amount,
                        "station": station
                    }
                ],
                "content": result_name
            }

    return out

if __name__ == "__main__":
    #print(parse_to_object_format("{{recipes/register\n| version = {{eversions|1.3.0.1|code=y}}\n| result = Greater Healing Potion | resultid = 499 | amount = 3\n| station = Placed Bottle\n| Bottled Water | 3\n| Pixie Dust | 3\n| Crystal Shard | 1\n}}"))
    recipes = get_all_recipes()

    with open("data/data/recipes_new.json", "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=4)