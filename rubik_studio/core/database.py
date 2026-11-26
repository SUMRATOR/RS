from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from rubik_studio.config import config
from rubik_studio.core.audit_logger import system_log


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(config.get_db_url(), echo=False, future=True)
        if config.db_type == "sqlite":
            _enable_sqlite_foreign_keys(_engine)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


def backup_database(keep: int = 3) -> None:
    """Резервное копирование SQLite через Backup API."""

    if config.db_type != "sqlite":
        return

    db_file = Path(config.db_path)

    if not db_file.exists():
        return

    if keep < 1:
        raise ValueError("keep должен быть >= 1")

    temporary = db_file.with_suffix(
        db_file.suffix + ".backup_tmp"
    )

    try:
        source_connection = sqlite3.connect(
            f"{db_file.resolve().as_uri()}?mode=ro",
            uri=True,
            timeout=30,
        )

        destination_connection = sqlite3.connect(temporary)

        try:
            source_connection.backup(destination_connection)

            result = destination_connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()

            if result != ("ok",):
                raise RuntimeError(
                    "Резервная копия не прошла проверку целостности"
                )

        finally:
            destination_connection.close()
            source_connection.close()

        for i in range(keep - 1, 0, -1):
            old = db_file.with_suffix(
                db_file.suffix + f".bak{i}"
            )
            new = db_file.with_suffix(
                db_file.suffix + f".bak{i + 1}"
            )

            if old.exists():
                shutil.copy2(old, new)

        temporary.replace(
            db_file.with_suffix(db_file.suffix + ".bak1")
        )

        system_log.info(
            "Создана резервная копия SQLite."
        )

    except Exception as exc:
        system_log.warning(
            "Не удалось создать резервную копию БД: %s",
            exc,
        )



def check_integrity() -> bool:
    """Проверка целостности SQLite через PRAGMA integrity_check."""
    if config.db_type != "sqlite":
        return True
    db_file = Path(config.db_path)
    if not db_file.exists():
        return True
    try:
        conn = sqlite3.connect(str(db_file))
        try:
            cursor = conn.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            ok = bool(result) and result[0] == "ok"
            if not ok:
                system_log.error("Проверка целостности БД не пройдена: %s", result)
            return ok
        finally:
            conn.close()
    except sqlite3.Error as exc:
        system_log.error("Ошибка при проверке целостности БД: %s", exc)
        return False



def _enable_sqlite_foreign_keys(engine):
    """Включение внешних ключей для каждого соединения SQLite."""

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()



async def init_db() -> None:
    """Создаёт таблицы (если их нет) и наполняет начальными данными."""
    from rubik_studio.core import models  # noqa: F401  регистрация моделей в метаданных

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # RS_V14_AUTO_INIT_V1
    if engine.url.get_backend_name() == "sqlite":
        import asyncio
        from rubik_studio.core.diagram_v14_auto_init import ensure_v14
        await asyncio.to_thread(
            ensure_v14, engine.url.database
        )
    await _seed_data()
    system_log.info("База данных инициализирована: %s", config.get_db_url())


async def _seed_data() -> None:
    from sqlalchemy import select

    from rubik_studio.auth.users import hash_password
    from rubik_studio.core.models import ObjectType, User, Methodology

    factory = get_session_factory()
    async with factory() as session:
        # RS_OBJECT_TYPES_SEED_30_V5
        # Существующие системные типы не изменяются.
        # Пользовательский тип не может занимать системный код.
        seed_types = [
            ('ORGANIZATION', 'Организация', 'business', '#1565C0'),
            ('DEPARTMENT', 'Подразделение', 'apartment', '#6D4C41'),
            ('POSITION', 'Должность', 'badge', '#3949AB'),
            ('EMPLOYEE', 'Сотрудник', 'person', '#1976D2'),
            ('ROLE', 'Роль', 'supervisor_account', '#1976D2'),
            ('PROCESS', 'Процесс', 'account_tree', '#2E7D32'),
            ('OPERATION', 'Операция', 'settings', '#388E3C'),
            ('FUNCTION', 'Функция', 'functions', '#43A047'),
            ('BUSINESS_EVENT', 'Бизнес-событие', 'event', '#00897B'),
            ('RESOURCE', 'Ресурс', 'inventory', '#795548'),
            ('EQUIPMENT', 'Оборудование', 'precision_manufacturing', '#757575'),
            ('MATERIAL', 'Материал', 'category', '#8D6E63'),
            ('DOCUMENT', 'Документ', 'description', '#F9A825'),
            ('DATA', 'Данные', 'storage', '#0277BD'),
            ('SYSTEM', 'Система', 'computer', '#5E35B1'),
            ('INFORMATION_FLOW', 'Информационный поток', 'sync_alt', '#00838F'),
            ('GOAL', 'Цель', 'flag', '#43A047'),
            ('MANAGEMENT_TASK', 'Управленческая задача', 'assignment', '#5C6BC0'),
            ('KPI', 'Показатель', 'trending_up', '#00838F'),
            ('REQUIREMENT', 'Требование', 'rule', '#7B1FA2'),
            ('REGULATION', 'Регламент', 'gavel', '#455A64'),
            ('RISK', 'Риск', 'warning', '#C62828'),
            ('CONTROL', 'Контроль', 'verified_user', '#2E7D32'),
            ('NONCONFORMITY', 'Несоответствие', 'error_outline', '#E64A19'),
            ('CUSTOMER', 'Клиент', 'people', '#0288D1'),
            ('PRODUCT', 'Продукт', 'shopping_bag', '#689F38'),
            ('SERVICE', 'Услуга', 'support_agent', '#0097A7'),
            ('BUSINESS_SERVICE', 'Бизнес-сервис', 'hub', '#512DA8'),
            ('APPLICATION', 'Приложение', 'apps', '#673AB7'),
            ('TECH_COMPONENT', 'Технический компонент', 'memory', '#546E7A'),
        ]

        seed_codes = [item[0] for item in seed_types]

        result = await session.execute(
            select(ObjectType).where(
                ObjectType.code.in_(seed_codes)
            )
        )

        existing_types = {
            item.code: item
            for item in result.scalars().all()
        }

        for code, name, icon, color in seed_types:
            existing = existing_types.get(code)

            if existing is not None:
                if not existing.is_system or existing.database_id is not None:
                    raise RuntimeError(
                        "Системный код типа объекта занят "
                        f"несистемным типом: {code}. "
                        "Начальное заполнение остановлено; "
                        "обратитесь к администратору."
                    )
                continue

            session.add(
                ObjectType(
                    code=code,
                    name=name,
                    icon=icon,
                    color=color,
                    database_id=None,
                    is_system=True,
                )
            )

        result = await session.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none() is None:
            session.add(
                User(
                    username="admin",
                    display_name="Администратор",
                    password_hash=hash_password("admin"),
                    role="admin",
                    is_active=True,
                )
            )

        # RS_SYSTEM_METHODOLOGIES_SEED_V1

        system_methodologies = [
            (
                "STANDARD",
                "Стандартная",
                "Стандартная методология моделирования",
            ),
            (
                "EXTENDED",
                "Расширенная",
                "Расширенная методология моделирования",
            ),
            (
                "FULL",
                "Полная",
                "Полный каталог типов моделей",
            ),
        ]

        for code, name, description in system_methodologies:

            result = await session.execute(
                select(Methodology).where(
                    Methodology.code == code
                )
            )

            existing = result.scalar_one_or_none()

            if existing is None:
                session.add(
                    Methodology(
                        code=code,
                        name=name,
                        description=description,
                    )
                )

        await session.commit()
