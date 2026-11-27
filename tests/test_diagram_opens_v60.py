"""Диаграмма обязана открываться: регрессия TypeError в V59.

Пользователь получил `TypeError: replace() argument 2 must be str, not
int` — NiceGUI отдаёт id компонента числом, а скрипт перетаскивания
подставлял его в строку как есть. Диаграмма не открывалась вовсе.

Тесты проверяют:
1. attach_drag_script принимает и число, и строку;
2. вспомогательный скрипт не может уронить открытие редактора;
3. страница редактора действительно строится (симулятор NiceGUI).
"""

from __future__ import annotations

import pathlib

import pytest
from nicegui import ui
from nicegui.testing import User

from rubik_studio.ui.bpmn_palette_v59 import DRAG_SCRIPT, attach_drag_script

pytest_plugins = ["nicegui.testing.user_plugin"]

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_attach_accepts_numeric_id():
    """Числовой id компонента не должен ломать подстановку."""
    captured = []

    @ui.page("/drag-numeric")
    def page():
        attach_drag_script(12345)

    # Скрипт собирается без исключения: подстановка приводит id к строке.
    assert DRAG_SCRIPT.replace("CANVAS_ID", str(12345)).count("12345") >= 1
    assert captured == []


def test_attach_rejects_non_alphanumeric_id():
    """Подозрительный id не попадает в JS-код."""
    with pytest.raises(ValueError):
        attach_drag_script("12'); alert(1)//")


def test_drag_script_is_guarded_in_editor():
    """Ошибка вспомогательного скрипта не роняет открытие диаграммы."""
    source = (
        ROOT / "rubik_studio/ui/pages/diagram_editor_v16.py"
    ).read_text(encoding="utf-8")

    assert "RS_PALETTE_DRAG_GUARD_V60" in source
    assert "attach_drag_script(canvas.id)" in source
    assert "logger.warning(" in source


async def test_editor_page_builds(user: User, isolated_database):
    """Редактор строится через настоящую точку входа создания диаграммы."""
    from rubik_studio.core import database
    from rubik_studio.core.modeling_databases import modeling_service
    from rubik_studio.ui.pages.diagram_editor_v16 import open_model_editor
    from rubik_studio.ui.pages.experimental_bpmn_v40 import _create_diagram

    await database.init_db()
    base = await modeling_service.create_database(name="Открытие диаграмм")
    model_id, model_name = await _create_diagram(
        base.id, "Процесс закупки", ""
    )

    @ui.page("/bpmn-v60")
    async def page():
        await open_model_editor(
            database_id=base.id,
            database_name="Открытие диаграмм",
            model_id=model_id,
            model_name=model_name,
        )

    await user.open("/bpmn-v60")
    await user.should_see("Процесс закупки")
