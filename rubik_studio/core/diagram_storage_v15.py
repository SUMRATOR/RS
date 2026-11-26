# RS_DIAGRAM_STORAGE_SERVICE_V15
"""
Хранение визуального содержимого существующих моделей в таблицах V14.

Сервис не создаёт модели и не определяет доступность редакторов.
Не использует таблицу model_element_bindings: размещения и линии
хранятся в отдельных таблицах rs_diagram_*.

Требуется SQLite со схемой V14 и включёнными внешними ключами.
"""

from __future__ import annotations

import datetime
import math
import uuid

from sqlalchemy import text

# RS_BPMN_SYMBOLS_V39
from sqlalchemy.exc import IntegrityError, OperationalError

from rubik_studio.core import diagram_symbols_v39 as symbols_v39
from rubik_studio.core.database import get_session_factory

MAX_NODES = 500
MAX_EDGES = 2000
MAX_LABEL_LENGTH = 500
MAX_COORDINATE = 100000.0


class DiagramStorageError(Exception):
    pass


class DiagramConflict(DiagramStorageError):
    pass


def _uuid_key(value, title):
    try:
        return uuid.UUID(str(value)).hex
    except (ValueError, TypeError, AttributeError) as exc:
        raise DiagramStorageError(
            f"Неверный идентификатор: {title}."
        ) from exc


def _number(value, title, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DiagramStorageError(f"Некорректное значение: {title}.")

    value = float(value)

    if not math.isfinite(value):
        raise DiagramStorageError(f"Некорректное значение: {title}.")

    if value < 0 or value > MAX_COORDINATE:
        raise DiagramStorageError(f"Значение вне диапазона: {title}.")

    if positive and value == 0:
        raise DiagramStorageError(f"Значение должно быть больше нуля: {title}.")

    return value


def validate_content(nodes, edges):
    """
    Проверить структуру входных данных до обращения к БД.

    node: id, object_id, x, y, width, height
    edge: id, source_node_id, target_node_id, label
    """
    if not isinstance(nodes, list) or len(nodes) > MAX_NODES:
        raise DiagramStorageError("Некорректный список элементов.")

    if not isinstance(edges, list) or len(edges) > MAX_EDGES:
        raise DiagramStorageError("Некорректный список линий.")

    clean_nodes = []
    node_ids = set()

    for node in nodes:
        if not isinstance(node, dict):
            raise DiagramStorageError("Некорректный элемент диаграммы.")

        node_id = _uuid_key(node.get("id"), "элемент")
        object_id = _uuid_key(node.get("object_id"), "объект")

        if node_id in node_ids:
            raise DiagramStorageError("Повторяется идентификатор элемента.")

        node_ids.add(node_id)

        clean_nodes.append({
            "id": node_id,
            "object_id": object_id,
            "x": _number(node.get("x"), "x"),
            "y": _number(node.get("y"), "y"),
            "width": _number(node.get("width"), "ширина", positive=True),
            "height": _number(node.get("height"), "высота", positive=True),
        })

    clean_edges = []
    edge_ids = set()

    for edge in edges:
        if not isinstance(edge, dict):
            raise DiagramStorageError("Некорректная линия.")

        edge_id = _uuid_key(edge.get("id"), "линия")
        source = _uuid_key(edge.get("source_node_id"), "начало линии")
        target = _uuid_key(edge.get("target_node_id"), "конец линии")
        label = edge.get("label", "")

        if edge_id in edge_ids:
            raise DiagramStorageError("Повторяется идентификатор линии.")

        if source == target:
            raise DiagramStorageError("Линия не может соединять элемент сам с собой.")

        if source not in node_ids or target not in node_ids:
            raise DiagramStorageError("Линия ссылается на отсутствующий элемент.")

        if not isinstance(label, str) or len(label) > MAX_LABEL_LENGTH:
            raise DiagramStorageError("Некорректная подпись линии.")

        edge_ids.add(edge_id)
        clean_edges.append({
            "id": edge_id,
            "source_node_id": source,
            "target_node_id": target,
            "label": label,
        })

    return clean_nodes, clean_edges


async def _rs_original_check_sqlite_exe_fix_v1(session):
    bind = session.get_bind()

    if bind.dialect.name != "sqlite":
        raise DiagramStorageError(
            "Схема V14 предназначена только для SQLite. "
            "Для другой СУБД требуется отдельная реализация."
        )

    enabled = (await session.execute(text("PRAGMA foreign_keys"))).scalar()

    if enabled != 1:
        raise DiagramStorageError(
            "В SQLite отключены внешние ключи. Сохранение запрещено."
        )

    try:
        rows = (await session.execute(text(
            "SELECT singleton, version "
            "FROM rs_diagram_storage_version"
        ))).all()
    except OperationalError as exc:
        raise DiagramStorageError(
            "Таблицы V14 отсутствуют в базе, используемой приложением. "
            "Проверьте, в какую базу был установлен V14."
        ) from exc

    if rows != [(1, 1)]:
        raise DiagramStorageError("Неподдерживаемая версия схемы V14.")


# RS_V14_SESSION_CHECK_EXE_FIX_V1
async def _check_sqlite(session):
    """
    Сначала выполняет исходную проверку V15.

    Если она сообщает об отсутствии V14, повторно проверяет таблицы
    через соединение текущей сессии. Это важно для автономного EXE:
    база приложения может находиться вне папки сборки.
    """
    try:
        return await _rs_original_check_sqlite_exe_fix_v1(session)
    except Exception as original_error:
        message = str(original_error).casefold()

        # Не подавляем другие ошибки исходной проверки.
        if not (
            "таблицы v14 отсутствуют" in message
            or "таблицы v14 отсутствуют в базе" in message
        ):
            raise

        from sqlalchemy import text

        bind = session.get_bind()
        if bind is None or bind.dialect.name != "sqlite":
            raise

        try:
            result = await session.execute(
                text("PRAGMA database_list")
            )
            databases = result.fetchall()

            main_paths = [
                row[2]
                for row in databases
                if row[1] == "main"
            ]

            if len(main_paths) != 1 or not main_paths[0]:
                raise RuntimeError(
                    "Не удалось определить файл основной SQLite-базы "
                    "текущего соединения."
                )

            required = {
                "rs_diagram_storage_version": {
                    "singleton", "version",
                },
                "rs_diagram_layouts": {
                    "model_id", "database_id", "revision", "updated_at",
                },
                "rs_diagram_nodes": {
                    "id", "model_id", "database_id", "object_id",
                    "x", "y", "width", "height",
                },
                "rs_diagram_edges": {
                    "id", "model_id", "database_id",
                    "source_node_id", "target_node_id", "label",
                },
            }

            result = await session.execute(
                text(
                    "SELECT name FROM main.sqlite_master "
                    "WHERE type = 'table'"
                )
            )
            tables = {row[0] for row in result.fetchall()}

            missing_tables = set(required) - tables
            if missing_tables:
                raise RuntimeError(
                    "В базе текущей сессии (" + str(main_paths[0]) + ") отсутствуют таблицы V14: "
                    + ", ".join(sorted(missing_tables))
                )

            for table_name, required_columns in required.items():
                # Имена здесь заданы константами, не пользовательским вводом.
                result = await session.execute(
                    text(
                        'PRAGMA main.table_info("' + table_name + '")'
                    )
                )
                columns = {row[1] for row in result.fetchall()}
                missing_columns = required_columns - columns

                if missing_columns:
                    raise RuntimeError(
                        "В таблице " + table_name
                        + " отсутствуют столбцы: "
                        + ", ".join(sorted(missing_columns))
                    )

            result = await session.execute(
                text(
                    "SELECT singleton, version "
                    "FROM main.rs_diagram_storage_version"
                )
            )
            versions = result.fetchall()

            if len(versions) != 1 or tuple(versions[0]) != (1, 1):
                raise RuntimeError(
                    "Неожиданная версия хранилища диаграмм V14: "
                    + repr([tuple(row) for row in versions])
                )

            result = await session.execute(text("PRAGMA foreign_keys"))
            if result.scalar() != 1:
                raise RuntimeError(
                    "Для текущего SQLite-соединения отключены "
                    "внешние ключи."
                )

        except Exception as verification_error:
            raise RuntimeError(
                "Повторная проверка V14 через соединение приложения "
                "не пройдена: " + str(verification_error)
            ) from verification_error

        # Выводим фактический путь, чтобы он был виден в журнале EXE.
        print(
            "RS V14: таблицы найдены через соединение приложения. "
            "База: " + str(main_paths[0]),
            flush=True,
        )
        return None



async def _model_identity(session, database_id, model_id):
    database_key = _uuid_key(database_id, "база")
    model_key = _uuid_key(model_id, "модель")

    rows = (await session.execute(
        text(
            "SELECT id, database_id FROM models "
            "WHERE lower(replace(CAST(id AS TEXT), '-', '')) = :model "
            "AND lower(replace(CAST(database_id AS TEXT), '-', '')) = :database"
        ),
        {"model": model_key, "database": database_key},
    )).all()

    if len(rows) != 1:
        raise DiagramStorageError(
            "Модель не найдена в выбранной базе "
            "или её идентификатор неоднозначен."
        )

    return rows[0][0], rows[0][1]


async def load_diagram(database_id, model_id):
    """
    Вернуть revision, nodes и edges.

    Названия объектов берутся из репозитория при каждой загрузке.
    Если размещение ещё не сохранялось, revision равен 0.
    """
    factory = get_session_factory()

    try:
        async with factory() as session:
            async with session.begin():
                await _check_sqlite(session)
                actual_model, actual_database = await _model_identity(
                    session, database_id, model_id
                )

                layout = (await session.execute(
                    text(
                        "SELECT revision FROM rs_diagram_layouts "
                        "WHERE model_id = :model AND database_id = :database"
                    ),
                    {"model": actual_model, "database": actual_database},
                )).first()

                if layout is None:
                    return {"revision": 0, "nodes": [], "edges": []}

                node_rows = (await session.execute(
                    text(
                        "SELECT n.id, n.object_id, o.name, "
                        "n.x, n.y, n.width, n.height "
                        "FROM rs_diagram_nodes AS n "
                        "JOIN objects AS o "
                        "ON o.id = n.object_id "
                        "AND o.database_id = n.database_id "
                        "WHERE n.model_id = :model "
                        "AND n.database_id = :database "
                        "ORDER BY n.id"
                    ),
                    {"model": actual_model, "database": actual_database},
                )).all()

                edge_rows = (await session.execute(
                    text(
                        "SELECT id, source_node_id, target_node_id, label "
                        "FROM rs_diagram_edges "
                        "WHERE model_id = :model "
                        "AND database_id = :database "
                        "ORDER BY id"
                    ),
                    {"model": actual_model, "database": actual_database},
                )).all()

                repository_nodes_v39 = [
                    {
                        "id": row[0],
                        "object_id": row[1],
                        "name": row[2],
                        "x": row[3],
                        "y": row[4],
                        "width": row[5],
                        "height": row[6],
                    }
                    for row in node_rows
                ]
                repository_edges_v39 = [
                    {
                        "id": row[0],
                        "source_node_id": row[1],
                        "target_node_id": row[2],
                        "label": row[3],
                    }
                    for row in edge_rows
                ]
                symbol_nodes_v39, symbol_edges_v39 = await symbols_v39.load_extra(
                    session, actual_model, actual_database,
                    validate_content,
                    repository_nodes_v39,
                    repository_edges_v39,
                )
                return {
                    "revision": int(layout[0]),
                    "nodes": repository_nodes_v39 + symbol_nodes_v39,
                    "edges": repository_edges_v39 + symbol_edges_v39,
                }

    except OperationalError as exc:
        raise DiagramStorageError(
            "Не удалось прочитать диаграмму из SQLite: " + str(exc)
        ) from exc


async def save_diagram(database_id, model_id, expected_revision, nodes, edges):
    """
    Атомарно сохранить полное содержимое модели.

    expected_revision берётся из load_diagram. Если другой пользователь
    сохранил модель раньше, возникает DiagramConflict.

    При успешном сохранении возвращается новая версия.
    """
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 0
    ):
        raise DiagramStorageError("Некорректная версия диаграммы.")

    clean_nodes, clean_edges, symbols_payload_v39 = symbols_v39.prepare(
        nodes, edges, validate_content
    )
    factory = get_session_factory()

    try:
        async with factory() as session:
            async with session.begin():
                await _check_sqlite(session)
                actual_model, actual_database = await _model_identity(
                    session, database_id, model_id
                )

                # Находим реальные значения ID объектов в этой базе.
                # Не подставляем идентификаторы из другой базы.
                object_rows = (await session.execute(
                    text(
                        "SELECT id FROM objects WHERE database_id = :database"
                    ),
                    {"database": actual_database},
                )).all()

                objects = {}
                for row in object_rows:
                    try:
                        key = _uuid_key(row[0], "объект в базе")
                    except DiagramStorageError:
                        continue

                    if key in objects:
                        raise DiagramStorageError(
                            "В базе обнаружены неоднозначные ID объектов."
                        )
                    objects[key] = row[0]

                for node in clean_nodes:
                    if node["object_id"] not in objects:
                        raise DiagramStorageError(
                            "Один из объектов отсутствует в выбранной базе. "
                            "Сохранение отменено."
                        )

                now = datetime.datetime.now(
                    datetime.UTC
                ).isoformat()

                if expected_revision == 0:
                    result = await session.execute(
                        text(
                            "INSERT INTO rs_diagram_layouts "
                            "(model_id, database_id, revision, updated_at) "
                            "VALUES (:model, :database, 1, :updated) "
                            "ON CONFLICT(model_id) DO NOTHING"
                        ),
                        {
                            "model": actual_model,
                            "database": actual_database,
                            "updated": now,
                        },
                    )

                    if result.rowcount != 1:
                        raise DiagramConflict(
                            "Диаграмма уже изменена в другом окне. "
                            "Перезагрузите её перед сохранением."
                        )

                    new_revision = 1

                else:
                    result = await session.execute(
                        text(
                            "UPDATE rs_diagram_layouts "
                            "SET revision = revision + 1, updated_at = :updated "
                            "WHERE model_id = :model "
                            "AND database_id = :database "
                            "AND revision = :expected"
                        ),
                        {
                            "model": actual_model,
                            "database": actual_database,
                            "expected": expected_revision,
                            "updated": now,
                        },
                    )

                    if result.rowcount != 1:
                        raise DiagramConflict(
                            "Диаграмма изменена или удалена в другом окне. "
                            "Перезагрузите её перед сохранением."
                        )

                    new_revision = expected_revision + 1

                # Символы и их линии сохраняются в той же
                # транзакции, после проверки revision.
                await symbols_v39.save_extra(
                    session, actual_model, actual_database,
                    symbols_payload_v39,
                )
                # Удаление старых элементов удалит их линии через CASCADE.
                await session.execute(
                    text(
                        "DELETE FROM rs_diagram_nodes "
                        "WHERE model_id = :model AND database_id = :database"
                    ),
                    {"model": actual_model, "database": actual_database},
                )

                for node in clean_nodes:
                    await session.execute(
                        text(
                            "INSERT INTO rs_diagram_nodes "
                            "(id, model_id, database_id, object_id, "
                            "x, y, width, height) "
                            "VALUES (:id, :model, :database, :object, "
                            ":x, :y, :width, :height)"
                        ),
                        {
                            "id": node["id"],
                            "model": actual_model,
                            "database": actual_database,
                            "object": objects[node["object_id"]],
                            "x": node["x"],
                            "y": node["y"],
                            "width": node["width"],
                            "height": node["height"],
                        },
                    )

                for edge in clean_edges:
                    await session.execute(
                        text(
                            "INSERT INTO rs_diagram_edges "
                            "(id, model_id, database_id, "
                            "source_node_id, target_node_id, label) "
                            "VALUES (:id, :model, :database, "
                            ":source, :target, :label)"
                        ),
                        {
                            "id": edge["id"],
                            "model": actual_model,
                            "database": actual_database,
                            "source": edge["source_node_id"],
                            "target": edge["target_node_id"],
                            "label": edge["label"],
                        },
                    )

            return new_revision

    except DiagramStorageError:
        raise
    except IntegrityError as exc:
        raise DiagramStorageError(
            "Сохранение отменено из-за нарушения целостности данных. "
            "Возможно, модель или объект были изменены."
        ) from exc
    except OperationalError as exc:
        raise DiagramStorageError(
            "Не удалось сохранить диаграмму в SQLite. "
            "Возможно, база занята или V14 установлен в другую базу: "
            + str(exc)
        ) from exc
