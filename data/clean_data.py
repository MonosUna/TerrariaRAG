import json
import os
import re

def remove_accent_chars(text: str) -> str:
    """Удаляет символы ударения"""
    return re.sub(r'\u0301', '', text)

def replace_wikilinks(text: str) -> str:
    """Заменяет все [[...]] на последнюю часть после |"""
    def repl(match):
        inner = match.group(1)
        return inner.split("|")[-1].strip()

    return re.sub(r"\[\[([^\[\]]+)\]\]", repl, text)

def process_templates(text: str, handler):
    """
    Преобразует все шаблоны {{...}} в текст, используя handler.

    :param text: исходный текст с шаблонами
    :param handler: функция handler(template_name: str, args: list[str]) -> str
    :return: текст с обработанными шаблонами
    """

    def template_replacer(match):
        tpl = match.group(0).strip('{}')
        parts = tpl.split('|')
        template_name = parts[0].strip('\n ')
        args = [p.strip() for p in parts[1:]]
        return handler(template_name, args)

    pattern = re.compile(r'\{\{[^{}]*\}\}')
    while re.search(pattern, text):
        text = re.sub(pattern, template_replacer, text)
    return text

def remove_classes(text: str) -> str:
    text = re.sub(r'\{\|.*?\|\}', '', text, flags=re.DOTALL)
    return text

def my_handler(name, args):
    if name.lower() == "recipes" or name.lower() == "recipes/register":
        if len(args) > 0 and "expectedrows" in args[-1]:
            return ""
        return "(Рецепт: " + ", ".join(args) + ")\n"
    elif name.lower() == "achievement":
        return "(Достижение: " + ", ".join(args) + ")\n"
    elif name.lower() == "history":
        return "(История: " + ", ".join(args) + ")\n"
    elif name.lower() == "item infobox":
        return "(Параметры предмета: " + ", ".join(args) + ")\n"
    elif name.lower() == "npc infobox":
        return "(Параметры NPC: " + ", ".join(args) + ")\n"
    elif name.lower() == "drop infobox":
        return ""
    elif name.lower() == "buff infobox":
        return "(Параметры баффа: " + ", ".join(args) + ")\n"
    else:
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
    text = re.sub(r"<.*?>.*?</.*?>", "", text, flags=re.DOTALL | re.IGNORECASE)
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
    content = remove_classes(content)
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
    #print(process_templates("{{item infobox\n| type = Potion\n| auto = 2359\n}}", my_handler))
#    print(clean_entry({
#    "title": "Согревающее зелье",
#    "pageid": 13623,
#    "ns": 0,
#    "timestamp": "2025-10-04T13:05:37Z",
#    "user": "KUBE",
#    "content": "{{aq|3}}\n{{legacy nav tab}}\n{{exclusive|1.2.4}}\n{{item infobox\n| type = Potion\n| auto = 2359\n}}\n\n'''Зелье тепла''' ({{ориг}}) − [[Зелья бафов|зелье бафа]], которое дает [[Бафы|баф]] '''Согревание'''  при использовании. Баф [[Снижение урона|уменьшает урон]] от [[Противники|врагов]] с холодной тематикой ''(см. [[#Затронутые сущности|ниже]])'' на 30%. {{buffduration}}\n\n== Создание ==\n=== Рецепт ===\n{{recipes|result=Warmth Potion|expectedrows=1}}\n\n== Затронутые сущности ==\nПока действует бафф «Согревание», урон от следующих врагов будет уменьшен:\n{{itemlist/options|class=terraria|width=12em}}\n{{#af_template:itemlist|{{#af_map:{{npcinfo query|stat=coldDamage|value=true|sort=name}}|npc|{{item|{{{npc}}}|icons=no|maxsize=50x50px}}}}}}\n{{itemlist/options|reset}}\nБаф «согревание» уменьшает как контактный урон от этих врагов, так и урон от их снарядов. Исключение составляют только Теневая рука Циклоп-оленя<!-- projectile 965: coldDamage=false --> и пули Снеговик-гангстера <!-- projectile 110: coldDamage=false --> — на них усиление «согревание» не действует. Обратите внимание, что урон от снаряда Циклоп-оленя всегда уменьшается, даже если они иногда выглядит как грязь или камень.\n\nКроме того, некоторые снаряды игрока [[Список отражаемых снарядов|отраженные]] [[Селенит]]ом, [[Подражатели#Особые_вариации|биомным мимиком]], [[Дреднаутилус|Дреднаутилусом]] или [[Мерцающий слизень|Мерцающем слизнем]] также будут наносить уменьшенный урон, пока активен баф. Это применяется после того, как исходный урон снаряда уменьшается вдвое при отражении. Затрагиваются снаряды следующего оружия:<!--\n\nthese projectiles can be reflected and have \"coldDamage\" set\n-->{{#arraydefine:list|118, 119, 120, 166, 172, 253, 309, 337, 344, 359, 520, 979|,}}<!--\n\n-->{{#vardefine:source_118|[[Ледяной клинок]]}}<!--\n-->{{#vardefine:source_119|[[Ледяной меч]]}}<!--\n-->{{#vardefine:source_120|[[Ледяной лук]] используя любые [[Стрелы]]}}<!--\n-->{{#vardefine:source_166|[[Снежок]], [[Снежная пушка]], [[Снежкомёт]]}}<!--\n-->{{#vardefine:source_172|Любой стандартный [[Луки|лук]]/[[Самострелы|самострел]] используя [[Стрела обжигающего холода|стрелы обжигающего холода]]}}<!--\n-->{{#vardefine:source_253|[[Морозный цветок]]}}<!--\n-->{{#vardefine:source_309|[[Посох ледяной гидры|ледяная гидра]]}}<!--\n-->{{#vardefine:source_337|[[Посох снежной бури]]}}<!--\n-->{{#vardefine:source_344|[[Северный полюс]]}}<!--\n-->{{#vardefine:source_359|[[Морозный посох]]}}<!--\n-->{{#vardefine:source_520|[[Морозная рыба-меч]], [[Рыбак]]}}<!--\n-->{{#vardefine:source_979|[[Палочка для заморозки]]}}<!--\n-->{{options/set|item|icons=no|mode=table|nolink=y|class=block aligncenter}}<!--\n-->{{flexstart}}<!-- этот flexbox гарантирует, что таблица будет отображаться рядом с {{item infobox}} на более широких экранах (а не под ним) -->\n{| class=\"terraria sortable full-width mw-collapsible mw-collapsed\"\n|-\n! colspan=4 | Снаряды\n|-\n! [[Идентификаторы снарядов|ID]] !! Изображение !! Название !! Источник\n{{#arrayprint:list|\n|@@@@|<tr>\n<td>@@@@</td>\n<td>[[File:{{projectileinfo|@@@@|image}}|link=]]</td>\n<td>{{projectileinfo|@@@@|name}}</td>\n<td>{{#var:source_@@@@|{{na}}}}</td>\n</tr>\n}}\n|}{{options/reset|item}}\n{{flexend}}\n\n== Примечания ==\n* Эффект «Согревания» не влияет на урон ледяного оружия в режиме [[PvP|Игрок против игрока]].\n* Снижение урона можно комбинировать с аналогичными эффектами других предметов, таких как [[Зелье выносливости]]. ''Подробнее см. в [[Снижение урона]].''\n* Усиление тепла не снижает урон [[Замёрзший зомби|замёрзшего зомби]], несмотря на то, что он является врагом, ориентированным на холод.\n\n== Советы ==\n* Согревающее зелье очень полезно во время [[События|событий]] [[Морозный легион]] и [[Морозная луна]] , так как многие из их врагов подвержены усилению тепла. Кроме того, оно будет действовать в течение всей продолжительности Морозной луны.\n* Зелье полезно во время битвы с [[Циклоп-олень|Циклоп-оленем]], хотя оно и не снижает урон от его снарядов теневой руки.\n\n== Интересные факты ==\n* Несмотря на свое название, баф согревания не защищает от дебафа [[Переохлаждение]], которое требует [[аксессуары]], такие как [[Варежки]].\n* [[Морозный гольян]] и [[ледошип]], которые являются ингредиентами для создания зелья тепла, оба добываются в [[Снежный биом|снежном биоме]], который сам по себе является биомом с холодной тематикой.\n\n== История ==\n{{history|Desktop 1.4.4|\n** Лимит стака увеличен с  30 до 9999.\n** Теперь также снижает урон от контакта с ледяной летучей мышью, ледяной черепахой, ледяным мимиком и йети.}}\n{{history|Desktop 1.4.0.1|Теперь также уменьшает контактный урон от снеговика-ганстера. Урон от его снежных пуль остается неизменным.}}\n{{history|Desktop 1.3.0.1|Спрайт обновлён.}}\n{{history|Desktop 1.2.4|Добавлен.}}\n\n{{Master Template Consumables\n| show-buff = yes\n}}\n{{Master Template Buffs\n| show-buffs = yes\n}}\n\n{{language info|en=Warmth Potion}}"
#  }))
#   print("content", "{{aq|3}}\n{{legacy nav tab}}\n{{exclusive|1.2.4}}\n{{item infobox\n| type = Potion\n| auto = 2359\n}}\n\n'''Зелье тепла''' ({{ориг}}) − [[Зелья бафов|зелье бафа]], которое дает [[Бафы|баф]] '''Согревание'''  при использовании. Баф [[Снижение урона|уменьшает урон]] от [[Противники|врагов]] с холодной тематикой ''(см. [[#Затронутые сущности|ниже]])'' на 30%. {{buffduration}}\n\n== Создание ==\n=== Рецепт ===\n{{recipes|result=Warmth Potion|expectedrows=1}}\n\n== Затронутые сущности ==\nПока действует бафф «Согревание», урон от следующих врагов будет уменьшен:\n{{itemlist/options|class=terraria|width=12em}}\n{{#af_template:itemlist|{{#af_map:{{npcinfo query|stat=coldDamage|value=true|sort=name}}|npc|{{item|{{{npc}}}|icons=no|maxsize=50x50px}}}}}}\n{{itemlist/options|reset}}\nБаф «согревание» уменьшает как контактный урон от этих врагов, так и урон от их снарядов. Исключение составляют только Теневая рука Циклоп-оленя<!-- projectile 965: coldDamage=false --> и пули Снеговик-гангстера <!-- projectile 110: coldDamage=false --> — на них усиление «согревание» не действует. Обратите внимание, что урон от снаряда Циклоп-оленя всегда уменьшается, даже если они иногда выглядит как грязь или камень.\n\nКроме того, некоторые снаряды игрока [[Список отражаемых снарядов|отраженные]] [[Селенит]]ом, [[Подражатели#Особые_вариации|биомным мимиком]], [[Дреднаутилус|Дреднаутилусом]] или [[Мерцающий слизень|Мерцающем слизнем]] также будут наносить уменьшенный урон, пока активен баф. Это применяется после того, как исходный урон снаряда уменьшается вдвое при отражении. Затрагиваются снаряды следующего оружия:<!--\n\nthese projectiles can be reflected and have \"coldDamage\" set\n-->{{#arraydefine:list|118, 119, 120, 166, 172, 253, 309, 337, 344, 359, 520, 979|,}}<!--\n\n-->{{#vardefine:source_118|[[Ледяной клинок]]}}<!--\n-->{{#vardefine:source_119|[[Ледяной меч]]}}<!--\n-->{{#vardefine:source_120|[[Ледяной лук]] используя любые [[Стрелы]]}}<!--\n-->{{#vardefine:source_166|[[Снежок]], [[Снежная пушка]], [[Снежкомёт]]}}<!--\n-->{{#vardefine:source_172|Любой стандартный [[Луки|лук]]/[[Самострелы|самострел]] используя [[Стрела обжигающего холода|стрелы обжигающего холода]]}}<!--\n-->{{#vardefine:source_253|[[Морозный цветок]]}}<!--\n-->{{#vardefine:source_309|[[Посох ледяной гидры|ледяная гидра]]}}<!--\n-->{{#vardefine:source_337|[[Посох снежной бури]]}}<!--\n-->{{#vardefine:source_344|[[Северный полюс]]}}<!--\n-->{{#vardefine:source_359|[[Морозный посох]]}}<!--\n-->{{#vardefine:source_520|[[Морозная рыба-меч]], [[Рыбак]]}}<!--\n-->{{#vardefine:source_979|[[Палочка для заморозки]]}}<!--\n-->{{options/set|item|icons=no|mode=table|nolink=y|class=block aligncenter}}<!--\n-->{{flexstart}}<!-- этот flexbox гарантирует, что таблица будет отображаться рядом с {{item infobox}} на более широких экранах (а не под ним) -->\n{| class=\"terraria sortable full-width mw-collapsible mw-collapsed\"\n|-\n! colspan=4 | Снаряды\n|-\n! [[Идентификаторы снарядов|ID]] !! Изображение !! Название !! Источник\n{{#arrayprint:list|\n|@@@@|<tr>\n<td>@@@@</td>\n<td>[[File:{{projectileinfo|@@@@|image}}|link=]]</td>\n<td>{{projectileinfo|@@@@|name}}</td>\n<td>{{#var:source_@@@@|{{na}}}}</td>\n</tr>\n}}\n|}{{options/reset|item}}\n{{flexend}}\n\n== Примечания ==\n* Эффект «Согревания» не влияет на урон ледяного оружия в режиме [[PvP|Игрок против игрока]].\n* Снижение урона можно комбинировать с аналогичными эффектами других предметов, таких как [[Зелье выносливости]]. ''Подробнее см. в [[Снижение урона]].''\n* Усиление тепла не снижает урон [[Замёрзший зомби|замёрзшего зомби]], несмотря на то, что он является врагом, ориентированным на холод.\n\n== Советы ==\n* Согревающее зелье очень полезно во время [[События|событий]] [[Морозный легион]] и [[Морозная луна]] , так как многие из их врагов подвержены усилению тепла. Кроме того, оно будет действовать в течение всей продолжительности Морозной луны.\n* Зелье полезно во время битвы с [[Циклоп-олень|Циклоп-оленем]], хотя оно и не снижает урон от его снарядов теневой руки.\n\n== Интересные факты ==\n* Несмотря на свое название, баф согревания не защищает от дебафа [[Переохлаждение]], которое требует [[аксессуары]], такие как [[Варежки]].\n* [[Морозный гольян]] и [[ледошип]], которые являются ингредиентами для создания зелья тепла, оба добываются в [[Снежный биом|снежном биоме]], который сам по себе является биомом с холодной тематикой.\n\n== История ==\n{{history|Desktop 1.4.4|\n** Лимит стака увеличен с  30 до 9999.\n** Теперь также снижает урон от контакта с ледяной летучей мышью, ледяной черепахой, ледяным мимиком и йети.}}\n{{history|Desktop 1.4.0.1|Теперь также уменьшает контактный урон от снеговика-ганстера. Урон от его снежных пуль остается неизменным.}}\n{{history|Desktop 1.3.0.1|Спрайт обновлён.}}\n{{history|Desktop 1.2.4|Добавлен.}}\n\n{{Master Template Consumables\n| show-buff = yes\n}}\n{{Master Template Buffs\n| show-buffs = yes\n}}\n\n{{language info|en=Warmth Potion}}"
#)
    clean_all()
