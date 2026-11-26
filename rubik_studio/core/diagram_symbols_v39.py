# RS_BPMN_SYMBOLS_V39
"""
Самостоятельные символы экспериментальной диаграммы.

Они не создают объекты репозитория.

Дополнительное содержимое сохраняется в SQLite в одной транзакции
с V15 и защищено той же проверкой revision.

Это экспериментальная основа, а не полный BPMN-редактор.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import text

TABLE = "rs_diagram_symbols_v39"
MAX_PAYLOAD = 4_000_000

SYMBOLS = {
    "START_EVENT": "Начальное событие",
    "INTERMEDIATE_EVENT": "Промежуточное событие",
    "END_EVENT": "Конечное событие",
    "TASK": "Задача",
    "SUBPROCESS": "Подпроцесс",
    "EXCLUSIVE_GATEWAY": "Исключающий шлюз",
    "PARALLEL_GATEWAY": "Параллельный шлюз",
    "INCLUSIVE_GATEWAY": "Включающий шлюз",
    "PARTICIPANT": "Участник",
    "LANE": "Дорожка",
}


def _key(value):
    return uuid.UUID(str(value)).hex


def _fail(message):
    # Импорт внутри функции не создаёт циклического импорта.
    from rubik_studio.core.diagram_storage_v15 import DiagramStorageError
    raise DiagramStorageError(message)


def prepare(nodes, edges, validate_content):
    """
    Проверить общее содержимое средствами V15 и разделить его на:
      - обычные размещения и линии между ними;
      - самостоятельные символы и линии с их участием.
    """
    if not isinstance(nodes, list) or not isinstance(edges, list):
        _fail("Некорректное содержимое диаграммы.")

    temporary_nodes = []
    symbol_info = {}

    for node in nodes:
        if not isinstance(node, dict):
            _fail("Некорректный элемент диаграммы.")

        kind = node.get("symbol_type")

        if kind is None:
            temporary_nodes.append(dict(node))
            continue

        if kind not in SYMBOLS:
            _fail("Неизвестный тип символа диаграммы.")

        name = node.get("name", SYMBOLS[kind])
        if not isinstance(name, str) or len(name) > 500:
            _fail("Некорректное название символа.")

        try:
            node_id = _key(node.get("id"))
        except Exception:
            _fail("Некорректный идентификатор символа.")

        if node_id in symbol_info:
            _fail("Повторяется идентификатор символа.")

        symbol_info[node_id] = {
            "symbol_type": kind,
            "name": name,
        }

        # Временный object_id нужен только для общей проверки V15.
        # В репозиторий этот идентификатор не записывается.
        temporary = dict(node)
        temporary["object_id"] = uuid.UUID(int=0).hex
        temporary_nodes.append(temporary)

    clean_nodes, clean_edges = validate_content(temporary_nodes, edges)

    repository_nodes = []
    symbol_nodes = []

    for node in clean_nodes:
        info = symbol_info.get(node["id"])
        if info is None:
            repository_nodes.append(node)
        else:
            symbol_nodes.append({
                "id": node["id"],
                "object_id": None,
                "symbol_type": info["symbol_type"],
                "name": info["name"],
                "x": node["x"],
                "y": node["y"],
                "width": node["width"],
                "height": node["height"],
            })

    repository_edges = []
    symbol_edges = []

    for edge in clean_edges:
        if (
            edge["source_node_id"] in symbol_info
            or edge["target_node_id"] in symbol_info
        ):
            symbol_edges.append(edge)
        else:
            repository_edges.append(edge)

    payload = json.dumps(
        {
            "version": 1,
            "nodes": symbol_nodes,
            "edges": symbol_edges,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )

    if len(payload.encode("utf-8")) > MAX_PAYLOAD:
        _fail("Слишком большой объём данных символов.")

    return repository_nodes, repository_edges, payload


async def _table_exists(session):
    result = await session.execute(
        text(
            "SELECT type FROM sqlite_master "
            "WHERE name = :name"
        ),
        {"name": TABLE},
    )
    rows = result.all()

    if not rows:
        return False

    if rows != [("table",)]:
        _fail("Имя таблицы символов занято другим объектом SQLite.")

    columns = (
        await session.execute(text("PRAGMA table_info(rs_diagram_symbols_v39)"))
    ).all()

    names = [str(row[1]) for row in columns]

    if names != ["model_id", "database_id", "payload"]:
        _fail("Обнаружена несовместимая таблица символов V39.")

    if not columns or int(columns[0][5]) != 1:
        _fail("Некорректный первичный ключ таблицы символов V39.")

    return True


async def ensure_table(session):
    if await _table_exists(session):
        return

    # Не предполагаем схему V14 только по номеру версии.
    layout_columns = (
        await session.execute(text("PRAGMA table_info(rs_diagram_layouts)"))
    ).all()

    layout_names = {str(row[1]) for row in layout_columns}

    if not {"model_id", "database_id", "revision"} <= layout_names:
        _fail("Таблица размещений V14 имеет неожиданную схему.")

    # model_id ссылается на существующий layout.
    await session.execute(text(
        "CREATE TABLE rs_diagram_symbols_v39 ("
        "model_id TEXT PRIMARY KEY, "
        "database_id TEXT NOT NULL, "
        "payload TEXT NOT NULL, "
        "FOREIGN KEY(model_id) "
        "REFERENCES rs_diagram_layouts(model_id) "
        "ON DELETE CASCADE"
        ")"
    ))

    if not await _table_exists(session):
        _fail("Не удалось создать таблицу символов.")


async def load_extra(session, model_id, database_id, validate_content,
                     repository_nodes, repository_edges):
    if not await _table_exists(session):
        return [], []

    rows = (
        await session.execute(
            text(
                "SELECT database_id, payload "
                "FROM rs_diagram_symbols_v39 "
                "WHERE model_id = :model"
            ),
            {"model": model_id},
        )
    ).all()

    if not rows:
        return [], []

    if len(rows) != 1 or str(rows[0][0]) != str(database_id):
        _fail("Нарушена принадлежность символов выбранной базе.")

    raw = rows[0][1]

    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_PAYLOAD:
        _fail("Некорректные данные символов.")

    try:
        data = json.loads(raw)
    except Exception as exc:
        _fail("Не удалось прочитать данные символов: " + str(exc))

    if not isinstance(data, dict) or data.get("version") != 1:
        _fail("Неподдерживаемая версия данных символов.")

    symbols = data.get("nodes")
    extra_edges = data.get("edges")

    if not isinstance(symbols, list) or not isinstance(extra_edges, list):
        _fail("Некорректный состав данных символов.")

    # Проверяем всё вместе: лимиты, UUID, координаты и концы линий.
    repo_nodes, repo_edges, normalized_payload = prepare(
        list(repository_nodes) + symbols,
        list(repository_edges) + extra_edges,
        validate_content,
    )

    normalized = json.loads(normalized_payload)

    # Дополнительная таблица не должна содержать обычные линии,
    # иначе при следующем сохранении они окажутся в другой таблице.
    if len(normalized["edges"]) != len(extra_edges):
        _fail("В таблице символов обнаружены несовместимые линии.")

    if len(repo_nodes) != len(repository_nodes):
        _fail("Некорректный состав размещений.")

    if len(repo_edges) != len(repository_edges):
        _fail("Некорректный состав линий.")

    return normalized["nodes"], normalized["edges"]


async def save_extra(session, model_id, database_id, payload):
    await ensure_table(session)

    # Проверяем, что уже существующая запись относится к той же базе.
    rows = (
        await session.execute(
            text(
                "SELECT database_id FROM rs_diagram_symbols_v39 "
                "WHERE model_id = :model"
            ),
            {"model": model_id},
        )
    ).all()

    if rows and (len(rows) != 1 or str(rows[0][0]) != str(database_id)):
        _fail("Нарушена принадлежность символов выбранной базе.")

    await session.execute(
        text(
            "INSERT INTO rs_diagram_symbols_v39 "
            "(model_id, database_id, payload) "
            "VALUES (:model, :database, :payload) "
            "ON CONFLICT(model_id) DO UPDATE SET "
            "database_id = excluded.database_id, "
            "payload = excluded.payload"
        ),
        {
            "model": model_id,
            "database": database_id,
            "payload": payload,
        },
    )


# RS_BPMN_VISUAL_FIX_V42
# Подписи в списке выбора. Коды и сохранённые данные не меняются.
SYMBOLS.update({
    "EXCLUSIVE_GATEWAY": "Шлюз: исключающее ИЛИ",
    "PARALLEL_GATEWAY": "Шлюз: И — все ветви",
    "INCLUSIVE_GATEWAY": "Шлюз: И/ИЛИ — одна или несколько ветвей",
})


# RS_BPMN_DATA_SYMBOLS_V48
# Коды сохраняются в данных диаграммы.
SYMBOLS.update({
    "DATA_INPUT": "Входные данные",
    "DATA_OUTPUT": "Выходные данные",
    "DATA_COLLECTION": "Набор данных",
})
