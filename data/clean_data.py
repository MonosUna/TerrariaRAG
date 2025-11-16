import json
import os
import re
import regex

def remove_accent_chars(text: str) -> str:
    """Удаляет символы ударения"""
    return re.sub(r'\u0301', '', text)

def replace_wikilinks(text: str) -> str:
    """
    Рекурсивно заменяет все [[...]] на последнюю часть после |.
    
    Пример:
    [[ a | [[ b | c ]] ]] -> [[ b | c ]] -> c
    """

    # рекурсивный паттерн для [[...]]
    pattern = regex.compile(r"\[\[([^\[\]]*(?:\[\[.*?\]\][^\[\]]*)*)\]\]")

    def repl(match: regex.Match) -> str:
        inner = match.group(1).strip()
        # берём последнюю часть после верхнеуровневого |
        parts = regex.split(r'\|(?![^\[]*\])', inner)
        last = parts[-1].strip()
        return last

    while True:
        new_text, count = pattern.subn(repl, text)
        if count == 0:
            break
        text = new_text

    return text

def remove_triple_braces(text: str) -> str:
    """
    Удаляет только конструкции вида {{{ ... }}}, поддерживает вложенные {{{...}}}.
    НЕ трогает {} и {{...}}.
    """
    res = []
    i = 0
    n = len(text)
    # стек для уровней тройных скобок — целое число depth
    depth = 0

    while i < n:
        # обнаружили тройное открытие
        if text.startswith("{{{", i):
            depth += 1
            i += 3
            # пропускаем всё до соответствующего количества '}}}'
            while i < n and depth > 0:
                if text.startswith("{{{", i):
                    depth += 1
                    i += 3
                elif text.startswith("}}}", i):
                    depth -= 1
                    i += 3
                else:
                    i += 1
            # после выхода — либо depth==0 (нашёлся закрывающий), либо конец строки
            continue

        # если не внутри тройных — просто копируем символ
        res.append(text[i])
        i += 1

    return "".join(res)

def split_top_level(s):
    parts = []
    buf = []
    depth = 0

    for c in s:
        if c == '{' and buf[-1:] == ['{']:
            depth += 1
            buf.append(c)
        elif c == '}' and buf[-1:] == ['}'] and depth > 0:
            depth -= 1
            buf.append(c)
        elif c == '|' and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(c)

    parts.append("".join(buf))
    return parts


def process_templates(text: str, handler):
    pattern = regex.compile(r"\{\{((?:[^{}]|(?R))*)\}\}", regex.DOTALL)

    def template_replacer(match: regex.Match) -> str:
        inner = match.group(1).strip()
        if not inner:
            return ""

        parts = split_top_level(inner)
        name = parts[0].strip()
        args = [p.strip() for p in parts[1:]]

        return handler(name, args)

    while True:
        new_text, count = pattern.subn(template_replacer, text)
        if count == 0:
            break
        text = new_text

    return text

def process_tables(text: str) -> str:
    result = []
    i = 0
    n = len(text)
    depth = 0

    while i < n:
        # начало таблицы
        if text.startswith("{|", i):
            depth += 1
            i += 2
            continue

        # конец таблицы
        if depth > 0 and text.startswith("|}", i):
            depth -= 1
            i += 2
            continue

        # внутри таблицы — пропускаем
        if depth > 0:
            i += 1
            continue

        # обычный текст
        result.append(text[i])
        i += 1

    return "".join(result)


def my_handler(name, args):
    name_l = name.lower()
    if len(args) == 0:
        return name

    if name_l == "item infobox":
        return f"(Параметры предмета: {', '.join(args)})"

    if name_l == "npc infobox":
        return f"(Параметры NPC: {', '.join(args)})"

    if name_l == "buff infobox":
        return f"(Параметры баффа: {', '.join(args)})"

    if name_l in ("recipes", "recipes/register"):
        if args and "expectedrows" in args[-1]:
            return ""
        return f"(Рецепт: {', '.join(args)})"

    if name_l == "achievement":
        return f"(Достижение: {', '.join(args)})"

    if name_l == "item":
        return f"(Предмет: {args[-1] if args else ''})"
    
    if name_l == "history":
        return f"(История: {', '.join(args)})"

    return ""

def delete_useless_headers(text: str) -> str:
    """Удаляет заголовки секций, которые не несут полезной информации"""
    useless_headers = [
        "Рецепт",
        "Создание",
    ]
    for header in useless_headers:
        pattern = re.compile(rf"==+\s*{re.escape(header)}\s*==+.*?(?=(==+|$))", re.DOTALL)
        text = re.sub(pattern, "", text)
    return text

def change_templates(text: str) -> str:
    """Удаляет все шаблоны {{...}} включая вложенные"""
    pattern = re.compile(r"\{\{[^{}]*\}\}")
    while re.search(pattern, text):
        text = re.sub(pattern, "", text)
    return text

def change_main_word(text: str, new_word: str) -> str:
    """Заменяет главное слово в начале текста на новое"""
    content = re.sub(r"\'\'\'(.*?)\'\'\'", f"\'\'\'{new_word}\'\'\'", text, count=1)
    content = re.sub(r"\{\{ориг\}\}", new_word, content)
    content = re.sub(r"\{\{PAGENAME\}\}", new_word, content)
    return content

def remove_wiki_tags(text: str) -> str:
    """Удаляет <noinclude>...</noinclude> и подобные wiki-теги"""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<.*?>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"</.*?>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<.*?/>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<noinclude>.*?</noinclude>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<includeonly>.*?</includeonly>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<onlyinclude>.*?</onlyinclude>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text


def clean_entry(entry: dict) -> dict:
    """Очищает поле 'content'"""
    content = entry.get("content", "")
    title = entry.get("title", "")
    if not content:
        return entry
    content = change_main_word(content, title)
    content = remove_accent_chars(content)
    content = replace_wikilinks(content)
    content = remove_triple_braces(content)
    content = process_tables(content)
    content = process_templates(content, my_handler)
    content = change_templates(content)
    content = remove_wiki_tags(content)
    content = delete_useless_headers(content)

    # Убираем лишние пробелы и пустые строки
    content = re.sub(r"\n\s*\n+", "\n", content)
    content = re.sub(r"[ \t]{2,}", " ", content)
    content = content.strip()

    entry["content"] = content
    return entry


def clean_all(file_path="wiki_dump_raw.json", output_path="wiki_dump_cleaned.json"):
    """Очищает все записи и сохраняет обратно"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    with open(file_path, "r", encoding="utf-8") as infile:
        data = json.load(infile)
    cleaned_data = []
    for i, entry in enumerate(data):
        temp = clean_entry(data[entry])
        if not "row" in temp.get("title") and not "register" in temp.get("title"):
            cleaned_data.append(temp)
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} entries...")
        
    with open(output_path, "w", encoding="utf-8") as outfile:
        json.dump(cleaned_data, outfile, ensure_ascii=False, indent=4)

    print(f"✅ Cleaned data written to {output_path}. Total entries: {len(cleaned_data)}")

def test(ok):
    if ok:
        print(clean_entry({
            "title": "Мощность кирки",
            "pageid": 15283,
            "ns": 0,
            "timestamp": "2025-07-17T23:59:02Z",
            "user": "KUBE",
            "content": "{{aq|3}}\n{{automatic translation}}\n\n'''Мощность кирки''' — показатель, определяющий, насколько эффективно [[кирка]] или [[буры|бур]] разрушает [[блок]]и. Она влияет на количество ударов, необходимых для разрушения блока. Некоторые блоки разрушаются мгновенно, другие невозможно добыть при низкой мощности кирки. Мощность кирки ''не влияет'' на [[скорость добычи]], то есть на [[время использования]] за один удар, но при низкой мощности кирки может потребоваться несколько ударов для разрушения блока, что снижает общую скорость добычи и создаёт впечатление, что кирка работает медленнее.\n\n== Эффекты ==\n=== В игре ===\n{| class=\"terraria align-center\" id=\"in-game-table\"\n! rowspan=2 | Блок\n! rowspan=2 | Прочность\n! colspan=13 | Ударов киркой<br/>(минимальная мощность кирки)\n|-\n! {{item|mode=image|Copper Pickaxe}}<br/>(35)\n! {{item|mode=image|Iron Pickaxe}}<br/>(40)\n! {{item|mode=image|Silver Pickaxe}}<br/>(45)\n! {{item|mode=image|Tungsten Pickaxe}}<br/>(50)\n! {{item|mode=image|Gold Pickaxe}}<br/>(55)\n! {{item|mode=image|Nightmare Pickaxe}}<br/>(65)\n! {{item|mode=image|Deathbringer Pickaxe}}<br/>(70)\n! {{item|mode=image|Molten Pickaxe}}<br/>(100)\n! {{item|mode=image|Cobalt Pickaxe}}<br/>(110)\n! {{item|mode=image|Mythril Pickaxe}}<br/>(150)\n! {{item|mode=image|Pickaxe Axe}}<br/>(200)\n! {{item|mode=image|Picksaw}}<br/>(210)\n! {{item|mode=image|Luminite Pickaxes}}<br/>(225)\n|-\n| {{item|Dirt Block}}<ref name = \"grass\">Если блок покрыт [[трава|травой]] или [[мох|мхом]], первый удар будет потрачен на их удаление (см. шаг 5, [[Мощность кирки#Механика]]). Для всех кирок количество ударов увеличивается на 1.</ref><br/>{{item|Sand Block}}<br/>{{item|Clay Block}}<br/>{{item|Mud Block}}<ref name = \"grass\"/><br/>{{item|Silt Block}}<br/>{{item|Ash Block}}<br/>{{item|Snow Block}}<br/>{{item|Slush Block}}<br/>{{item|Hardened Sand Block}}<br/>{{item|Spike}} ({{eicons|1.4.0.1}})<br/>{{item|Wooden Spike}} ({{eicons|1.4.0.1}}) || 50%\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n|-\n| {{item|Stone Block}}<ref name = \"grass\"/><br/>{{item|Ebonsand Block}}<br/>{{item|Gold Ore}}<br/>{{item|Gray Brick}}<ref name = \"grass\"/><br/>все блоки, не указанные здесь || 100%\n| 3\n| 3\n| 3\n| 2\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n|-\n| {{item|Meteorite}} || 100%\n| {{na}}\n| {{na}}\n| {{na}}\n| 2\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n|-\n| {{item|Demonite Ore}}<ref name = \":2\"/><br/> {{item|Crimtane Ore}}<ref name = \":2\"/> || 100%\n| 3<ref name = \":2\">Руда [[демонит|демонита]] и [[багротановая руда|кримтана]] может быть добыта с мощностью кирки < 55% только выше уровня 0 футов.</ref>\n| 3<ref name = \":2\"/>\n| 3<ref name = \":2\"/>\n| 2<ref name = \":2\"/>\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n|-\n| {{item|Obsidian}} || 100%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{eicons|1.4.3.3}} 2<br/>{{eicons|1.4.3.3|invert=y}} {{na}}\n| 2\n| 2\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n|-\n| {{item|Ebonstone Block}}<br/>{{item|Pearlstone Block}}<br/>{{item|Hellstone}}<br/>{{item|Crimstone Block}}<br/> || 200%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 4\n| 3\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n|-\n| {{item|image=Blue Brick.png/Green Brick.png/Pink Brick.png|Dungeon Bricks}}<ref name = \":3\"/> || 200%\n| 6<ref name = \":3\">Кирпичи [[темница|темницы]] могут быть добыты с мощностью кирки {{eicons|1.4.3.3}} < 100% / {{eicons|1.4.3.3|invert=y}}< 65% только выше уровня 0 футов или в центральных 30% мира.</ref>\n| 5<ref name = \":3\"/>\n| 5<ref name = \":3\"/>\n| 4<ref name = \":3\"/>\n| 4<ref name = \":3\"/>\n| 4<ref name = \":3\"/>\n| 3<ref name = \":3\"/>\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n|-\n| {{item|Cobalt Ore}}<br/>{{item|Palladium Ore}} || 200%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n|-\n| {{item|Tombstone|s}} || 300%\n| 9\n| 8\n| 7\n| 6\n| 6\n| 5\n| 5\n| 3\n| 3\n| 2\n| 2\n| 2\n| 2\n|-\n| {{item|Mythril Ore}}<br/>{{item|Orichalcum Ore}} || 300%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 3\n| 2\n| 2\n| 2\n| 2\n|-\n| {{item|Adamantite Ore}}<br/>{{item|Titanium Ore}} || 400%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 3\n| 2\n| 2\n| 2\n|-\n| {{item|Spike}} ({{eicons|1.4.0.1|invert=y}})<br/>{{item|Wooden Spike}} ({{eicons|1.4.0.1|invert=y}}) || 400%\n| 12\n| 10\n| 9\n| 8\n| 8\n| 7\n| 6\n| 4\n| 4\n| 3\n| 2\n| 2\n| 2\n|-\n| {{item|Lihzahrd Brick}} || 400%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 2\n| 2\n|-\n| {{item|Chlorophyte Ore}} || 500%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 3\n| 3\n| 3\n|}\n\n{{reflist}}\n\n=== Механика ===\nКаждый блок изначально имеет 0 единиц урона. При каждом ударе [[инструменты#кирки и буры|киркой]] урон по блоку увеличивается следующим образом:\n# <code>damageIncrease = 0</code>\n# <code>damageIncrease = 100</code>, если выполняется одно из условий:\n#* Блок является [[объекты|растением или грибом на фоне]].\n#* Блок является лозой (например, [[порча|порченые]], [[багрянец|багряные]], [[джунгли|джунглевые]] лозы).\n#* Блок покрыт [[мох|мхом]].\n#* Блок является [[лиана|лианой]].\n#* Блок является [[факел]]ом.\n#* Блок является [[верёвка|верёвкой]].\n#* Блок является [[фоновые объекты|фоновым объектом]].\n#* Блок — [[хрупкий лёд]].\n#* Блок — [[Красители#Основные красители|растение для красителя]] или [[странное растение]].\n#* Блок — [[книга]].\n#* Блок — [[трава|лечебная трава]].\n#* Блок — [[кучи монет]].\n#* Блок — [[листья|живой лиственный блок]] или [[листья красного дерева|живой блок лиственного красного дерева]].\n#* Блок — [[семя тыквы]].\n#* Блок — [[осколок кристалла]].\n3. Добавляется мощность кирки к <code>damageIncrease</code>, с учётом модификаторов для определённых блоков:\n#* <code>damageIncrease = damageIncrease + Мощность кирки * 2</code> — для {{item|Dirt Block|блока земли}}, {{item|Clay Block|глины}}, {{item|Sand Block|песка}}, {{item|Hardened Sand Block|затвердевшего песка}}, {{item|Ash Block|пепла}}, {{item|Mud Block|блока грязи}}, {{item|Silt Block|ила}}, {{item|Slush Block|слякоти}} и {{item|Snow Block|снега}}.\n#* <code>damageIncrease = damageIncrease + Мощность кирки / 2</code> — для {{item|Ebonstone Block|чёрного камня}}, {{item|Crimstone Block|багрового камня}}, {{item|Pearlstone Block|жемчужного камня}}, {{item|Hellstone|адского камня}}, {{item|Cobalt Ore|кобальтовой руды}}, {{item|Palladium Ore|палладиевой руды}} и всех {{item|image=Blue Brick.png/Green Brick.png/Pink Brick.png|Dungeon Bricks|кирпичей темницы}}.\n#* <code>damageIncrease = damageIncrease + Мощность кирки / 3</code> — для {{item|Mythril Ore|мифриловой руды}} и {{item|Mythril Ore|орихалковой руды}}.\n#* <code>damageIncrease = damageIncrease + Мощность кирки / 4</code> — для {{item|Mythril Ore|адамантитовой руды}}, {{item|Titanium Ore|титановой руды}}, {{item|Spike|шипов}}, {{item|Wooden Spike|деревянных шипов}} и {{item|Lihzahrd Brick|ящщерового кирпича}}.\n#* <code>damageIncrease = damageIncrease + Мощность кирки / 5</code> — для {{item|Chlorophyte Ore|хлорофитовой руды}}.\n#* <code>damageIncrease = damageIncrease + Мощность кирки</code> — для всех остальных блоков, например, {{item|Stone Block|камня}}, {{item|Red Brick|красного кирпича}} и т. д.\n4. <code>damageIncrease = 0</code>, если выполняется одно из условий:\n#* Мощность кирки < 210%, и блок — {{item|Lihzahrd Brick|ящщеровый кирпич}} или {{item|Lihzahrd Altar|ящщеровый алтарь}}.\n#* Мощность кирки < 200%, и блок — {{item|Chlorophyte Ore|хлорофитовая руда}}.\n#* Мощность кирки < 150%, и блок — {{item|Adamantite Ore|адамантитовая руда}} или {{item|Titanium Ore|титановая руда}}.\n#* Мощность кирки < 110%, и блок — {{item|Mythril Ore|мифриловая руда}} или {{item|Orichalcum Ore|орихалковая руда}}.\n#* Мощность кирки < 100%, и блок — {{item|Cobalt Ore|кобальтовая руда}} или {{item|Palladium Ore|палладиевая руда}}.\n#* Мощность кирки < 65%, и блок — {{item|Ebonstone Block|чёрный камень}}, {{item|Crimstone Block|багровый камень}}, {{item|Pearlstone Block|жемчужный камень}}, {{item|Hellstone|адский камень}}, {{item|Obsidian|обсидиан}} или {{item|Desert Fossil|окаменелое ископаемое}}.\n#* Мощность кирки < 65%, и блок — {{item|image=Blue Brick.png/Green Brick.png/Pink Brick.png|Dungeon Bricks|кирпичи темницы|кирпичи темницы}} вне центральных 30% мира.\n#* Мощность кирки < 55%, и блок — {{item|Demonite Ore|демонитовая руда}} или {{item|Crimtane Ore|кримтановая руда}} ниже поверхности.\n#* Мощность кирки < 50%, и блок — {{item|Meteorite|метеорит]].\n5. Если блок покрыт травой или мхом и <code>damageAmount + damageIncrease >= 100</code>, то <code>damageIncrease = 0</code>.\nКогда урон по блоку достигает 100, блок разрушается. Важно отметить, что даже если блок не разрушается после удара, он может измениться (например, травяной блок превратится в обычный блок грязи).\n\n== Примечания ==\n* {{eversions|Laser Drill|short}} Игроки могут получить максимальную мощность кирки (230%) с помощью [[лазерный бур|лазерного бура]]. {{eversions|Laser Drill|short|invert=y}} Игроки могут использовать [[киркопила|киркопилу]], которая имеет мощность кирки 210%. Оба инструмента способны добывать [[ящщеровый кирпич|ящщеровые кирпичи]].\n* {{icon/old-gen}} В старых версиях игрок может добывать блоки, такие как трава и мох, за 1 удар вместо 2, если мощность кирки достаточно высока.\n\n== Интересные факты ==\n* [[Лопата могильщика]] имеет внутреннюю мощность кирки 30. Это означает, что она добывает мягкие блоки за 2 удара, а некоторые блоки, например, заражённые варианты песка, — за 4 удара.\n\n== История ==\n{{history|Desktop-Release|Добавлено.}}\n{{history|Console-Release|Добавлено.}}\n{{history|Switch 1.0.711.6|Добавлено.}}\n{{history|Mobile-Release|Добавлено.}}\n{{history|3DS-Release|Добавлено.}}\n\n{{Game mechanics}}\n\n{{language info|en=Pickaxe power}}"
        },))    
        print({
            "title": "Мощность кирки",
            "pageid": 15283,
            "ns": 0,
            "timestamp": "2025-07-17T23:59:02Z",
            "user": "KUBE",
            "content": "{{aq|3}}\n{{automatic translation}}\n\n'''Мощность кирки''' — показатель, определяющий, насколько эффективно [[кирка]] или [[буры|бур]] разрушает [[блок]]и. Она влияет на количество ударов, необходимых для разрушения блока. Некоторые блоки разрушаются мгновенно, другие невозможно добыть при низкой мощности кирки. Мощность кирки ''не влияет'' на [[скорость добычи]], то есть на [[время использования]] за один удар, но при низкой мощности кирки может потребоваться несколько ударов для разрушения блока, что снижает общую скорость добычи и создаёт впечатление, что кирка работает медленнее.\n\n== Эффекты ==\n=== В игре ===\n{| class=\"terraria align-center\" id=\"in-game-table\"\n! rowspan=2 | Блок\n! rowspan=2 | Прочность\n! colspan=13 | Ударов киркой<br/>(минимальная мощность кирки)\n|-\n! {{item|mode=image|Copper Pickaxe}}<br/>(35)\n! {{item|mode=image|Iron Pickaxe}}<br/>(40)\n! {{item|mode=image|Silver Pickaxe}}<br/>(45)\n! {{item|mode=image|Tungsten Pickaxe}}<br/>(50)\n! {{item|mode=image|Gold Pickaxe}}<br/>(55)\n! {{item|mode=image|Nightmare Pickaxe}}<br/>(65)\n! {{item|mode=image|Deathbringer Pickaxe}}<br/>(70)\n! {{item|mode=image|Molten Pickaxe}}<br/>(100)\n! {{item|mode=image|Cobalt Pickaxe}}<br/>(110)\n! {{item|mode=image|Mythril Pickaxe}}<br/>(150)\n! {{item|mode=image|Pickaxe Axe}}<br/>(200)\n! {{item|mode=image|Picksaw}}<br/>(210)\n! {{item|mode=image|Luminite Pickaxes}}<br/>(225)\n|-\n| {{item|Dirt Block}}<ref name = \"grass\">Если блок покрыт [[трава|травой]] или [[мох|мхом]], первый удар будет потрачен на их удаление (см. шаг 5, [[Мощность кирки#Механика]]). Для всех кирок количество ударов увеличивается на 1.</ref><br/>{{item|Sand Block}}<br/>{{item|Clay Block}}<br/>{{item|Mud Block}}<ref name = \"grass\"/><br/>{{item|Silt Block}}<br/>{{item|Ash Block}}<br/>{{item|Snow Block}}<br/>{{item|Slush Block}}<br/>{{item|Hardened Sand Block}}<br/>{{item|Spike}} ({{eicons|1.4.0.1}})<br/>{{item|Wooden Spike}} ({{eicons|1.4.0.1}}) || 50%\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n|-\n| {{item|Stone Block}}<ref name = \"grass\"/><br/>{{item|Ebonsand Block}}<br/>{{item|Gold Ore}}<br/>{{item|Gray Brick}}<ref name = \"grass\"/><br/>все блоки, не указанные здесь || 100%\n| 3\n| 3\n| 3\n| 2\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n|-\n| {{item|Meteorite}} || 100%\n| {{na}}\n| {{na}}\n| {{na}}\n| 2\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n|-\n| {{item|Demonite Ore}}<ref name = \":2\"/><br/> {{item|Crimtane Ore}}<ref name = \":2\"/> || 100%\n| 3<ref name = \":2\">Руда [[демонит|демонита]] и [[багротановая руда|кримтана]] может быть добыта с мощностью кирки < 55% только выше уровня 0 футов.</ref>\n| 3<ref name = \":2\"/>\n| 3<ref name = \":2\"/>\n| 2<ref name = \":2\"/>\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n|-\n| {{item|Obsidian}} || 100%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{eicons|1.4.3.3}} 2<br/>{{eicons|1.4.3.3|invert=y}} {{na}}\n| 2\n| 2\n| 1\n| 1\n| 1\n| 1\n| 1\n| 1\n|-\n| {{item|Ebonstone Block}}<br/>{{item|Pearlstone Block}}<br/>{{item|Hellstone}}<br/>{{item|Crimstone Block}}<br/> || 200%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 4\n| 3\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n|-\n| {{item|image=Blue Brick.png/Green Brick.png/Pink Brick.png|Dungeon Bricks}}<ref name = \":3\"/> || 200%\n| 6<ref name = \":3\">Кирпичи [[темница|темницы]] могут быть добыты с мощностью кирки {{eicons|1.4.3.3}} < 100% / {{eicons|1.4.3.3|invert=y}}< 65% только выше уровня 0 футов или в центральных 30% мира.</ref>\n| 5<ref name = \":3\"/>\n| 5<ref name = \":3\"/>\n| 4<ref name = \":3\"/>\n| 4<ref name = \":3\"/>\n| 4<ref name = \":3\"/>\n| 3<ref name = \":3\"/>\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n|-\n| {{item|Cobalt Ore}}<br/>{{item|Palladium Ore}} || 200%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 2\n| 2\n| 2\n| 1\n| 1\n| 1\n|-\n| {{item|Tombstone|s}} || 300%\n| 9\n| 8\n| 7\n| 6\n| 6\n| 5\n| 5\n| 3\n| 3\n| 2\n| 2\n| 2\n| 2\n|-\n| {{item|Mythril Ore}}<br/>{{item|Orichalcum Ore}} || 300%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 3\n| 2\n| 2\n| 2\n| 2\n|-\n| {{item|Adamantite Ore}}<br/>{{item|Titanium Ore}} || 400%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 3\n| 2\n| 2\n| 2\n|-\n| {{item|Spike}} ({{eicons|1.4.0.1|invert=y}})<br/>{{item|Wooden Spike}} ({{eicons|1.4.0.1|invert=y}}) || 400%\n| 12\n| 10\n| 9\n| 8\n| 8\n| 7\n| 6\n| 4\n| 4\n| 3\n| 2\n| 2\n| 2\n|-\n| {{item|Lihzahrd Brick}} || 400%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 2\n| 2\n|-\n| {{item|Chlorophyte Ore}} || 500%\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| {{na}}\n| 3\n| 3\n| 3\n|}\n\n{{reflist}}\n\n=== Механика ===\nКаждый блок изначально имеет 0 единиц урона. При каждом ударе [[инструменты#кирки и буры|киркой]] урон по блоку увеличивается следующим образом:\n# <code>damageIncrease = 0</code>\n# <code>damageIncrease = 100</code>, если выполняется одно из условий:\n#* Блок является [[объекты|растением или грибом на фоне]].\n#* Блок является лозой (например, [[порча|порченые]], [[багрянец|багряные]], [[джунгли|джунглевые]] лозы).\n#* Блок покрыт [[мох|мхом]].\n#* Блок является [[лиана|лианой]].\n#* Блок является [[факел]]ом.\n#* Блок является [[верёвка|верёвкой]].\n#* Блок является [[фоновые объекты|фоновым объектом]].\n#* Блок — [[хрупкий лёд]].\n#* Блок — [[Красители#Основные красители|растение для красителя]] или [[странное растение]].\n#* Блок — [[книга]].\n#* Блок — [[трава|лечебная трава]].\n#* Блок — [[кучи монет]].\n#* Блок — [[листья|живой лиственный блок]] или [[листья красного дерева|живой блок лиственного красного дерева]].\n#* Блок — [[семя тыквы]].\n#* Блок — [[осколок кристалла]].\n3. Добавляется мощность кирки к <code>damageIncrease</code>, с учётом модификаторов для определённых блоков:\n#* <code>damageIncrease = damageIncrease + Мощность кирки * 2</code> — для {{item|Dirt Block|блока земли}}, {{item|Clay Block|глины}}, {{item|Sand Block|песка}}, {{item|Hardened Sand Block|затвердевшего песка}}, {{item|Ash Block|пепла}}, {{item|Mud Block|блока грязи}}, {{item|Silt Block|ила}}, {{item|Slush Block|слякоти}} и {{item|Snow Block|снега}}.\n#* <code>damageIncrease = damageIncrease + Мощность кирки / 2</code> — для {{item|Ebonstone Block|чёрного камня}}, {{item|Crimstone Block|багрового камня}}, {{item|Pearlstone Block|жемчужного камня}}, {{item|Hellstone|адского камня}}, {{item|Cobalt Ore|кобальтовой руды}}, {{item|Palladium Ore|палладиевой руды}} и всех {{item|image=Blue Brick.png/Green Brick.png/Pink Brick.png|Dungeon Bricks|кирпичей темницы}}.\n#* <code>damageIncrease = damageIncrease + Мощность кирки / 3</code> — для {{item|Mythril Ore|мифриловой руды}} и {{item|Mythril Ore|орихалковой руды}}.\n#* <code>damageIncrease = damageIncrease + Мощность кирки / 4</code> — для {{item|Mythril Ore|адамантитовой руды}}, {{item|Titanium Ore|титановой руды}}, {{item|Spike|шипов}}, {{item|Wooden Spike|деревянных шипов}} и {{item|Lihzahrd Brick|ящщерового кирпича}}.\n#* <code>damageIncrease = damageIncrease + Мощность кирки / 5</code> — для {{item|Chlorophyte Ore|хлорофитовой руды}}.\n#* <code>damageIncrease = damageIncrease + Мощность кирки</code> — для всех остальных блоков, например, {{item|Stone Block|камня}}, {{item|Red Brick|красного кирпича}} и т. д.\n4. <code>damageIncrease = 0</code>, если выполняется одно из условий:\n#* Мощность кирки < 210%, и блок — {{item|Lihzahrd Brick|ящщеровый кирпич}} или {{item|Lihzahrd Altar|ящщеровый алтарь}}.\n#* Мощность кирки < 200%, и блок — {{item|Chlorophyte Ore|хлорофитовая руда}}.\n#* Мощность кирки < 150%, и блок — {{item|Adamantite Ore|адамантитовая руда}} или {{item|Titanium Ore|титановая руда}}.\n#* Мощность кирки < 110%, и блок — {{item|Mythril Ore|мифриловая руда}} или {{item|Orichalcum Ore|орихалковая руда}}.\n#* Мощность кирки < 100%, и блок — {{item|Cobalt Ore|кобальтовая руда}} или {{item|Palladium Ore|палладиевая руда}}.\n#* Мощность кирки < 65%, и блок — {{item|Ebonstone Block|чёрный камень}}, {{item|Crimstone Block|багровый камень}}, {{item|Pearlstone Block|жемчужный камень}}, {{item|Hellstone|адский камень}}, {{item|Obsidian|обсидиан}} или {{item|Desert Fossil|окаменелое ископаемое}}.\n#* Мощность кирки < 65%, и блок — {{item|image=Blue Brick.png/Green Brick.png/Pink Brick.png|Dungeon Bricks|кирпичи темницы|кирпичи темницы}} вне центральных 30% мира.\n#* Мощность кирки < 55%, и блок — {{item|Demonite Ore|демонитовая руда}} или {{item|Crimtane Ore|кримтановая руда}} ниже поверхности.\n#* Мощность кирки < 50%, и блок — {{item|Meteorite|метеорит]].\n5. Если блок покрыт травой или мхом и <code>damageAmount + damageIncrease >= 100</code>, то <code>damageIncrease = 0</code>.\nКогда урон по блоку достигает 100, блок разрушается. Важно отметить, что даже если блок не разрушается после удара, он может измениться (например, травяной блок превратится в обычный блок грязи).\n\n== Примечания ==\n* {{eversions|Laser Drill|short}} Игроки могут получить максимальную мощность кирки (230%) с помощью [[лазерный бур|лазерного бура]]. {{eversions|Laser Drill|short|invert=y}} Игроки могут использовать [[киркопила|киркопилу]], которая имеет мощность кирки 210%. Оба инструмента способны добывать [[ящщеровый кирпич|ящщеровые кирпичи]].\n* {{icon/old-gen}} В старых версиях игрок может добывать блоки, такие как трава и мох, за 1 удар вместо 2, если мощность кирки достаточно высока.\n\n== Интересные факты ==\n* [[Лопата могильщика]] имеет внутреннюю мощность кирки 30. Это означает, что она добывает мягкие блоки за 2 удара, а некоторые блоки, например, заражённые варианты песка, — за 4 удара.\n\n== История ==\n{{history|Desktop-Release|Добавлено.}}\n{{history|Console-Release|Добавлено.}}\n{{history|Switch 1.0.711.6|Добавлено.}}\n{{history|Mobile-Release|Добавлено.}}\n{{history|3DS-Release|Добавлено.}}\n\n{{Game mechanics}}\n\n{{language info|en=Pickaxe power}}"
        },)
    
if __name__ == "__main__":
    ok = False
    test(ok)
    #print(clean_entry({"title":"a", "content":"{{#af_template:itemlist|{{#af_map:|npc|{{item|{{{}}}|icons=no|maxsize=50x50px}}}}}}"}))
    clean_all()

