from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path


REQUIRED = {
    "rs_diagram_storage_version": {"singleton", "version"},
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

DDL = (
    """
    CREATE TABLE rs_diagram_storage_version (
        singleton INTEGER NOT NULL PRIMARY KEY
            CHECK (singleton = 1),
        version INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE rs_diagram_layouts (
        model_id TEXT NOT NULL,
        database_id TEXT NOT NULL,
        revision INTEGER NOT NULL DEFAULT 0
            CHECK (revision >= 0),
        updated_at TEXT NOT NULL,
        PRIMARY KEY (model_id),
        UNIQUE (model_id, database_id),
        FOREIGN KEY (model_id, database_id)
            REFERENCES models (id, database_id)
            ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE rs_diagram_nodes (
        id TEXT NOT NULL PRIMARY KEY,
        model_id TEXT NOT NULL,
        database_id TEXT NOT NULL,
        object_id TEXT NOT NULL,
        x REAL NOT NULL CHECK (x >= 0),
        y REAL NOT NULL CHECK (y >= 0),
        width REAL NOT NULL CHECK (width > 0),
        height REAL NOT NULL CHECK (height > 0),
        UNIQUE (id, model_id, database_id),
        FOREIGN KEY (model_id, database_id)
            REFERENCES rs_diagram_layouts (model_id, database_id)
            ON DELETE CASCADE,
        FOREIGN KEY (object_id, database_id)
            REFERENCES objects (id, database_id)
            ON DELETE RESTRICT
    )
    """,
    """
    CREATE TABLE rs_diagram_edges (
        id TEXT NOT NULL PRIMARY KEY,
        model_id TEXT NOT NULL,
        database_id TEXT NOT NULL,
        source_node_id TEXT NOT NULL,
        target_node_id TEXT NOT NULL,
        label TEXT NOT NULL DEFAULT '',
        CHECK (source_node_id <> target_node_id),
        FOREIGN KEY (model_id, database_id)
            REFERENCES rs_diagram_layouts (model_id, database_id)
            ON DELETE CASCADE,
        FOREIGN KEY (source_node_id, model_id, database_id)
            REFERENCES rs_diagram_nodes (id, model_id, database_id)
            ON DELETE CASCADE,
        FOREIGN KEY (target_node_id, model_id, database_id)
            REFERENCES rs_diagram_nodes (id, model_id, database_id)
            ON DELETE CASCADE
    )
    """,
)


def _quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({_quote(table)})"
        )
    }


def _check_integrity(conn: sqlite3.Connection) -> None:
    integrity = conn.execute("PRAGMA integrity_check").fetchall()

    if integrity != [("ok",)]:
        raise RuntimeError(
            "SQLite integrity_check не пройден: "
            + repr(integrity[:20])
        )

    violations = conn.execute("PRAGMA foreign_key_check").fetchall()

    if violations:
        raise RuntimeError(
            "SQLite foreign_key_check обнаружил нарушения: "
            + repr(violations[:20])
        )


def _validate_v14(conn: sqlite3.Connection) -> None:
    present = _tables(conn)

    missing_tables = set(REQUIRED) - present
    if missing_tables:
        raise RuntimeError(
            "Отсутствуют таблицы V14: "
            + ", ".join(sorted(missing_tables))
        )

    for table, required_columns in REQUIRED.items():
        missing = required_columns - _columns(conn, table)

        if missing:
            raise RuntimeError(
                f"Таблица {table}: отсутствуют столбцы "
                + ", ".join(sorted(missing))
            )

    rows = conn.execute(
        "SELECT singleton, version FROM rs_diagram_storage_version"
    ).fetchall()

    if rows != [(1, 1)]:
        raise RuntimeError(
            "Неожиданная версия V14: " + repr(rows)
        )


def _has_unique_pair(conn: sqlite3.Connection, table: str) -> bool:
    for row in conn.execute(
        f"PRAGMA index_list({_quote(table)})"
    ).fetchall():
        name = row[1]
        unique = bool(row[2])
        partial = bool(row[4])

        if not unique or partial:
            continue

        columns = [
            item[2]
            for item in conn.execute(
                f"PRAGMA index_info({_quote(name)})"
            ).fetchall()
        ]

        if columns == ["id", "database_id"]:
            return True

    return False


def _ensure_unique_pair(
    conn: sqlite3.Connection,
    table: str,
    index_name: str,
) -> None:
    if _has_unique_pair(conn, table):
        return

    occupied = conn.execute(
        "SELECT type FROM sqlite_master WHERE name = ?",
        (index_name,),
    ).fetchone()

    if occupied:
        raise RuntimeError(
            "Имя индекса уже занято: " + index_name
        )

    conn.execute(
        f"CREATE UNIQUE INDEX {_quote(index_name)} "
        f"ON {_quote(table)} (id, database_id)"
    )


def _backup(conn: sqlite3.Connection, db_path: Path) -> Path:
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = db_path.with_name(
        db_path.name + ".before_v14_" + stamp + ".bak"
    )

    # Не перезаписываем существующую копию.
    with backup_path.open("xb"):
        pass

    try:
        destination = sqlite3.connect(str(backup_path), timeout=30)

        try:
            conn.backup(destination)
            _check_integrity(destination)
        finally:
            destination.close()

    except Exception:
        # Оставляем файл для диагностики, но не продолжаем миграцию.
        raise RuntimeError(
            "Не удалось создать проверенную резервную копию: "
            + str(backup_path)
        )

    return backup_path


def ensure_v14(db_filename: str) -> None:
    """
    Устанавливает отсутствующее хранилище V14 в существующую
    SQLite-базу. Частично установленную схему не изменяет.
    """
    if not db_filename or db_filename == ":memory:":
        raise RuntimeError(
            "Автоматическая установка V14 требует файловую SQLite-базу."
        )

    db_path = Path(db_filename).resolve()

    if not db_path.is_file():
        raise RuntimeError(
            "Файл SQLite для установки V14 не найден: " + str(db_path)
        )

    conn = sqlite3.connect(
        db_path.as_uri() + "?mode=rw",
        uri=True,
        timeout=30,
        isolation_level=None,
    )

    try:
        conn.execute("PRAGMA foreign_keys=ON")
        _check_integrity(conn)

        existing = _tables(conn)
        present = set(REQUIRED) & existing

        if present == set(REQUIRED):
            _validate_v14(conn)
            return

        if present:
            raise RuntimeError(
                "Хранилище V14 установлено частично. "
                "Автоматическое изменение остановлено: "
                + ", ".join(sorted(present))
            )

        for table in ("models", "objects"):
            if table not in existing:
                raise RuntimeError(
                    "Для установки V14 отсутствует таблица " + table
                )

            missing = {"id", "database_id"} - _columns(conn, table)
            if missing:
                raise RuntimeError(
                    f"Таблица {table} не соответствует текущей схеме: "
                    + ", ".join(sorted(missing))
                )

        data_version = conn.execute(
            "PRAGMA data_version"
        ).fetchone()[0]

        backup_path = _backup(conn, db_path)

        conn.execute("BEGIN IMMEDIATE")

        try:
            current_version = conn.execute(
                "PRAGMA data_version"
            ).fetchone()[0]

            if current_version != data_version:
                raise RuntimeError(
                    "База изменилась во время резервирования. "
                    "Перезапустите приложение."
                )

            if set(REQUIRED) & _tables(conn):
                raise RuntimeError(
                    "Схема V14 изменилась во время установки. "
                    "Перезапустите приложение."
                )

            _ensure_unique_pair(
                conn,
                "models",
                "rs_v14_models_id_database_id_uq",
            )
            _ensure_unique_pair(
                conn,
                "objects",
                "rs_v14_objects_id_database_id_uq",
            )

            for statement in DDL:
                conn.execute(statement)

            conn.execute(
                "INSERT INTO rs_diagram_storage_version "
                "(singleton, version) VALUES (1, 1)"
            )

            _validate_v14(conn)
            _check_integrity(conn)
            conn.execute("COMMIT")

        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise

        print(
            "RS: хранилище диаграмм V14 установлено. "
            "Резервная копия: " + str(backup_path),
            flush=True,
        )

    finally:
        conn.close()
