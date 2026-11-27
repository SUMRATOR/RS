"""Дымовые проверки страниц: каждая собирается без исключений.

Пользователь сообщил, что диаграммы не открываются, и просил провести
полную проверку на баги. Этот модуль открывает каждую страницу
приложения в симуляторе NiceGUI и проверяет, что построение прошло без
исключения и на странице есть ожидаемый заголовок.

Тесты не заменяют глазную проверку: они ловят падения при сборке
страницы (как TypeError из V59), но не проверяют вёрстку.
"""

from __future__ import annotations

import pytest
from nicegui import ui
from nicegui.testing import User

pytest_plugins = ["nicegui.testing.user_plugin"]


@pytest.fixture()
async def prepared(isolated_database):
    """Одна база с объектом, связью и диаграммой — для всех страниц."""
    from rubik_studio.core import database
    from rubik_studio.core.modeling_databases import modeling_service
    from rubik_studio.core.repository import repo_service
    from rubik_studio.ui.pages.experimental_bpmn_v40 import _create_diagram

    await database.init_db()

    existing = await repo_service.list_databases()
    base = existing[0] if existing else await modeling_service.create_database(
        name="Дымовая проверка"
    )

    types = await repo_service.list_types(database_id=base.id)
    doc_type = next(item for item in types if item.code == "DOCUMENT")
    customer_type = next(item for item in types if item.code == "CUSTOMER")

    await repo_service.create_object(
        database_id=base.id,
        type_id=doc_type.id,
        name="Заявка на закупку",
        description="Проверка страниц",
        username="tester",
    )
    await repo_service.create_object(
        database_id=base.id,
        type_id=customer_type.id,
        name="ООО Ромашка",
        description="",
        username="tester",
    )

    model_id, model_name = await _create_diagram(base.id, "Схема для проверки", "")

    return {"base": base, "model_id": model_id, "model_name": model_name}


async def test_login_page(user: User):
    from rubik_studio.ui.pages.login import render as render_login

    ui.page("/smoke-login")(render_login)
    await user.open("/smoke-login")
    await user.should_see("RS — RUBIK STUDIO")


async def test_home_page(user: User, prepared):
    from rubik_studio.main import rubik_home_page

    ui.page("/smoke-home")(rubik_home_page)
    await user.open("/smoke-home")
    await user.should_see("Объектов в репозитории")


async def test_repository_page(user: User, prepared):
    from rubik_studio.ui.pages.repository import render as render_repository

    ui.page("/smoke-repository")(render_repository)
    await user.open("/smoke-repository")
    await user.should_see("Репозиторий объектов")


async def test_databases_page(user: User, prepared):
    from rubik_studio.ui.pages.modeling_databases import render

    ui.page("/smoke-databases")(render)
    await user.open("/smoke-databases")
    await user.should_see("Базы моделирования")


async def test_settings_page(user: User, prepared):
    from rubik_studio.ui.pages.settings import render

    ui.page("/smoke-settings")(render)
    await user.open("/smoke-settings")
    await user.should_see("Настройки")


async def test_logs_page(user: User, prepared):
    from rubik_studio.ui.pages.logs_viewer import render

    ui.page("/smoke-logs")(render)
    await user.open("/smoke-logs")
    await user.should_see("Аудит-логи")


async def test_diagram_editor_opens(user: User, prepared):
    """Главная регрессия V59: редактор диаграммы должен открываться."""
    from rubik_studio.ui.pages.diagram_editor_v16 import open_model_editor

    data = prepared

    @ui.page("/smoke-editor")
    async def page():
        await open_model_editor(
            database_id=data["base"].id,
            database_name=data["base"].name,
            model_id=data["model_id"],
            model_name=data["model_name"],
        )

    await user.open("/smoke-editor")
    await user.should_see(data["model_name"])


async def test_object_card_opens_and_scrolls(user: User, prepared):
    """Карточка объекта открывается и имеет область прокрутки."""
    from rubik_studio.core.repository import repo_service
    from rubik_studio.ui.pages.repository import render as render_repository

    objects = await repo_service.list_objects(database_id=prepared["base"].id)
    target = next(item for item in objects if item.type and item.type.code == "DOCUMENT")

    ui.page("/smoke-card")(render_repository)
    await user.open("/smoke-card")

    user.find(marker=f"rs-object-edit-{target.id}").click()

    await user.should_see("Карточка объекта")
    await user.should_see("Файл документа")

    # Область прокрутки помечена, значит длинное содержимое не обрежется.
    assert user.find(marker="rs-object-card-scroll")
