# RS_CONFTEST_DB_V57
"""Общая подготовка тестов.

Тесты страниц поднимают настоящие страницы приложения, а те обращаются к
базе (список пользователей в настройках, аудит-лог). На машине разработчика
файл базы уже есть, поэтому локально всё проходило, а в CI на чистом клоне
тесты падали с «no such table: users».

Здесь создаётся временная база во временной папке: рабочая база
пользователя не затрагивается, тесты не зависят от её состояния и идут
одинаково на Linux и Windows.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def isolated_database():
    """Направить приложение на временную SQLite-базу на время тестов."""
    from rubik_studio.config import config
    from rubik_studio.core import database

    tmp_dir = Path(tempfile.mkdtemp(prefix="rs-tests-"))
    saved = (config.db_type, config.db_path, config.db_url)

    config.db_type = "sqlite"
    config.db_path = str(tmp_dir / "test.db")
    config.db_url = ""

    # Движок мог быть создан при импорте другого теста.
    database._engine = None
    database._session_factory = None

    asyncio.run(database.init_db())

    yield tmp_dir

    if database._engine is not None:
        asyncio.run(database._engine.dispose())
    database._engine = None
    database._session_factory = None
    config.db_type, config.db_path, config.db_url = saved
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def keep_user_config():
    """Тесты не должны менять рабочий config.json разработчика.

    Часть тестов меняет тему и сохраняет конфигурацию; после прогона
    возвращаем исходные значения и не пишем на диск рабочую копию.
    """
    from rubik_studio.config import config

    saved = (config.theme, config.theme_accent, config.theme_background)
    saved_save = config.save
    config.save = lambda *args, **kwargs: None

    yield

    config.save = saved_save
    config.theme, config.theme_accent, config.theme_background = saved
