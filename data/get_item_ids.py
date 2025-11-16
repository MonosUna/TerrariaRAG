import json

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

items = load_json("test/items.json")
recipes = load_json("test/recipes.json")
tables = load_json("test/tables.json")

# id → название предмета
item_id_to_name = {item["id"]: item["name"] for item in items}

# id → рабочая станция
table_id_to_name = {
    t["id"]: t["name"] if not t["alternate_name"] 
    else f"{t['name']} / {t['alternate_name']}"
    for t in tables
}

# итоговый словарь: сразу создаем пустые рецепты
result = {
    item["name"]: {"recipes": []}
    for item in items
}

# Проходимся по рецептам
for recipe in recipes:
    output_item_id = recipe["name"]
    output_name = item_id_to_name.get(output_item_id, "UNKNOWN")
    if output_name == "UNKNOWN":
        print(f"Warning: Unknown output item ID {output_item_id} in recipe.")
        continue

    station = table_id_to_name.get(recipe["table"], "Unknown station")

    # ингредиенты
    components = {}
    for i in range(1, 7):
        ing_id = recipe[f"ingredient{i}"]
        amt = recipe[f"amount{i}"]

        if ing_id.strip() and amt.strip():
            ing_name = item_id_to_name.get(ing_id, f"UNKNOWN_{ing_id}")
            components[ing_name] = int(amt)

    # добавить рецепт к предмету
    result[output_name]["recipes"].append({
        "components": components,
        "station": station
    })

# сохранить итог
with open("recipes.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=4)