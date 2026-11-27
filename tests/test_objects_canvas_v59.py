"""Проверка V59: типоспецифичные атрибуты, якоря стрелок, полотно.

Тесты без браузера. Проверяем то, что можно проверить автоматически:

1. набор атрибутов зависит от типа объекта (документ, клиент, процесс);
2. обязательные поля не дают сохранить пустую карточку;
3. карточка объекта в живом UI показывает поля своего типа;
4. точки присоединения стрелок считаются по видимой фигуре, а не по
   блоку 180 x 70;
5. лист диаграммы растёт под содержимое и не обрезает элементы.

Что эти тесты НЕ проверяют: как выглядят стрелки в браузере, работает
ли перетаскивание мышью и как ведёт себя панорамирование при реальном
перетаскивании. Это остаётся на ручную проверку.

Запуск:  pytest tests/test_objects_canvas_v59.py -v
"""

from __future__ import annotations

import pathlib
import re

import pytest

from rubik_studio.core.object_attributes_v59 import (
    CUSTOMER_SCHEMA,
    DOCUMENT_SCHEMA,
    GENERIC_SCHEMA,
    KIND_DATE,
    KIND_FILE,
    load_fields,
    missing_required,
    schema_for,
)

pytest_plugins = ["nicegui.testing.user_plugin"]

ROOT = pathlib.Path(__file__).resolve().parents[1]
EDITOR = ROOT / "rubik_studio/ui/pages/diagram_editor_v16.py"
PALETTE = ROOT / "rubik_studio/ui/bpmn_palette_v59.py"


# ── Атрибуты по типу объекта ───────────────────────────────────────────────

def test_document_schema_has_file_and_date():
    """У документа есть файл и даты — то, что просил пользователь."""
    kinds = {item.kind for item in DOCUMENT_SCHEMA.fields}
    assert KIND_FILE in kinds
    assert KIND_DATE in kinds
    titles = [item.title for item in DOCUMENT_SCHEMA.fields]
    assert "Дата документа" in titles


def test_customer_schema_has_full_name_and_date():
    """У клиента — ФИО и дата рождения."""
    titles = [item.title for item in CUSTOMER_SCHEMA.fields]
    assert "ФИО" in titles
    assert "Дата рождения" in titles


def test_schemas_differ_between_types():
    """Разные типы не получают одинаковый набор полей."""
    document = {item.key for item in schema_for("DOCUMENT").fields}
    customer = {item.key for item in schema_for("CUSTOMER").fields}
    assert document != customer


def test_unknown_type_gets_generic_schema():
    """Неизвестный тип не остаётся с пустым списком."""
    assert schema_for("НЕТ_ТАКОГО_ТИПА") is GENERIC_SCHEMA
    assert schema_for(None) is GENERIC_SCHEMA


def test_required_field_is_reported():
    """У клиента ФИО обязательно: пустая карточка не сохраняется."""
    missing = missing_required("CUSTOMER", {})
    assert [item.title for item in missing] == ["ФИО"]

    assert missing_required("CUSTOMER", {"full_name": "Иванов Иван"}) == []


def test_existing_custom_attributes_are_kept():
    """Свои атрибуты старых карточек не теряются при новом наборе."""
    fields = load_fields("DOCUMENT", {"Внутренний код": "A-1"})
    keys = [item.key for item in fields]

    assert "doc_number" in keys
    assert "Внутренний код" in keys


def test_no_duplicate_keys_in_schemas():
    """Внутри одного набора нет повторяющихся ключей."""
    for code in ("DOCUMENT", "CUSTOMER", "ORGANIZATION", "EMPLOYEE", "PROCESS"):
        keys = [item.key for item in schema_for(code).fields]
        assert len(keys) == len(set(keys)), code


# ── Карточка объекта в живом UI ────────────────────────────────────────────

async def test_document_card_shows_document_fields(user, isolated_database):
    """В карточке документа видны именно его поля."""
    from nicegui import ui

    from rubik_studio.core import database
    from rubik_studio.core.modeling_databases import modeling_service
    from rubik_studio.core.repository import repo_service
    from rubik_studio.ui.pages.repository import render as render_repository

    await database.init_db()

    # Временная база общая на весь прогон, поэтому страница репозитория
    # открывает первую базу в списке. Кладём объект именно в неё, иначе
    # тест зависел бы от порядка выполнения других тестов.
    existing = await repo_service.list_databases()
    base = existing[0] if existing else await modeling_service.create_database(
        name="Тест V59"
    )
    types = await repo_service.list_types(database_id=base.id)
    doc_type = next(item for item in types if item.code == "DOCUMENT")
    obj = await repo_service.create_object(
        database_id=base.id,
        type_id=doc_type.id,
        name="Заявка на закупку",
        description="",
        username="tester",
    )

    ui.page("/repository-v59")(render_repository)
    await user.open("/repository-v59")
    await user.should_see("Заявка на закупку")

    user.find(marker=f"rs-object-edit-{obj.id}").click()

    await user.should_see("Карточка объекта")
    await user.should_see("Номер документа")
    await user.should_see("Файл документа")

    # Полей другого типа в карточке документа быть не должно.
    with pytest.raises(AssertionError):
        await user.should_see("Дата рождения")


# ── Точки присоединения стрелок ────────────────────────────────────────────

def test_anchor_uses_visible_shape():
    """Точки связи считаются по видимой фигуре, а не по блоку элемента."""
    source = EDITOR.read_text(encoding="utf-8")

    assert "RS_DIAGRAM_ANCHOR_V59" in source
    # Радиус кружка и ромба берётся из видимой фигуры.
    assert "function visibleBox(" in source
    assert "box.rx = 29" in source
    assert "box.rx = 30" in source


def test_events_and_gateways_get_shape_attribute():
    """Форма задаётся по типу символа, а не по трём старым кодам."""
    source = EDITOR.read_text(encoding="utf-8")

    assert "BPMN_EVENT_KINDS_V59" in source
    assert "BPMN_GATEWAY_KINDS_V59" in source
    assert 'element.props(\'data-rs-shape="circle"\')' in source

    # Граничные события тоже считаются кружком.
    from rubik_studio.core.bpmn_shapes_v55 import EVENT_KINDS

    assert "BOUNDARY_MESSAGE" in EVENT_KINDS


# ── Бесконечный лист ───────────────────────────────────────────────────────

def test_canvas_extent_grows_with_nodes():
    """Лист увеличивается под содержимое и не обрезает элементы."""
    from rubik_studio.ui.pages.diagram_editor_v16 import (
        CANVAS_MARGIN,
        HEIGHT,
        WIDTH,
        canvas_extent,
    )

    assert canvas_extent([]) == (WIDTH, HEIGHT)

    width, height = canvas_extent(
        [{"x": 30000, "y": 40000, "width": 180, "height": 70}]
    )
    assert width == 30000 + 180 + CANVAS_MARGIN
    assert height == 40000 + 70 + CANVAS_MARGIN


def test_canvas_allows_nodes_beyond_sheet():
    """Элемент можно поставить дальше старой границы 20000."""
    from rubik_studio.ui.pages.diagram_editor_v16 import WORLD_LIMIT

    assert WORLD_LIMIT > 20000


def test_canvas_is_not_clipped():
    """Лист не обрезает содержимое по краю."""
    source = EDITOR.read_text(encoding="utf-8")

    assert "RS_INFINITE_CANVAS_V59" in source
    assert "overflow:visible" in source
    # Старая жёсткая рамка полотна убрана.
    assert 'border:1px solid #33415C; border-radius:10px;' not in source


# ── Палитра: сворачивание и перетаскивание ─────────────────────────────────

def test_palette_groups_collapse():
    """У групп палитры есть заголовок-переключатель."""
    palette = PALETTE.read_text(encoding="utf-8")

    assert "def collapse_group(" in palette
    assert "data-rs-group-toggle" in palette
    assert "render_items()" in palette


def test_symbol_card_is_draggable():
    """Карточка символа перетаскивается и принимается полем."""
    palette = PALETTE.read_text(encoding="utf-8")

    assert "data-rs-drag-symbol" in palette
    assert "rs-palette-drop-v59" in palette
    assert "pointerdown" in palette


def test_drop_event_wired_in_editor():
    """Поле диаграммы слушает сброс символа и ставит его под курсор."""
    source = EDITOR.read_text(encoding="utf-8")

    assert "rs-palette-drop-v59" in source
    assert "drop_x=world_x" in source


def test_event_tabs_fit_narrow_panel():
    """Вкладки положений стоят сеткой: в узкой панели они не обрезаются."""
    tabs = (
        ROOT / "rubik_studio/ui/bpmn_event_palette_v58.py"
    ).read_text(encoding="utf-8")

    assert "RS_EVENT_TABS_V59" in tabs
    assert "grid-template-columns:repeat(2, minmax(0, 1fr))" in tabs


# ── Макет страниц ──────────────────────────────────────────────────────────

def test_home_page_uses_shared_layout():
    """Главная собирается общим макетом: шапка, меню, тема."""
    main_source = (ROOT / "rubik_studio/main.py").read_text(encoding="utf-8")

    assert "RS_HOME_LAYOUT_V59" in main_source
    assert "render_dashboard" in main_source


def test_databases_page_uses_shared_layout():
    """«Базы моделирования» тоже получает шапку и тему."""
    source = (
        ROOT / "rubik_studio/ui/pages/modeling_databases.py"
    ).read_text(encoding="utf-8")

    assert "RS_DATABASES_LAYOUT_V59" in source
    assert "create_page_layout(" in source

    # Старая отдельная кнопка «На главную» больше не нужна: есть меню.
    assert 'ui.button(\n        "На главную"' not in source.replace("\r\n", "\n")


def test_layout_supports_subtitle():
    """Макет принимает пояснение под заголовком страницы."""
    layout = (ROOT / "rubik_studio/ui/layout.py").read_text(encoding="utf-8")
    assert re.search(r"def create_page_layout\(title: str, subtitle: str", layout)


# ── Вкладки положений событий ──────────────────────────────────────────────

async def test_position_tab_switch_highlights_and_shows_subtypes(user):
    """Клик по вкладке переключает подтипы и подсвечивает саму вкладку."""
    from nicegui import ui

    from rubik_studio.ui.bpmn_event_palette_v58 import (
        render_event_variants_palette,
    )

    @ui.page("/variants-v59")
    def page():
        render_event_variants_palette(on_pick=lambda kind: None)

    await user.open("/variants-v59")
    await user.should_see("С него начинается процесс")

    user.find(marker="rs-position-boundary").click()
    await user.should_see("Крепится к границе задачи или подпроцесса")

    user.find(marker="rs-position-end").click()
    await user.should_see("Им процесс заканчивается")


async def test_collapsed_group_hides_items_until_opened(user):
    """Свёрнутая группа не создаёт десятки карточек заранее."""
    from nicegui import ui

    from rubik_studio.ui.bpmn_palette_v59 import collapse_group

    @ui.page("/collapse-v59")
    def page():
        collapse_group(
            "Свёрнутая группа",
            3,
            lambda: [ui.label(f"элемент {index}") for index in range(3)],
            start_open=False,
            key="collapsed-demo",
        )

    await user.open("/collapse-v59")
    await user.should_see("Свёрнутая группа")

    with pytest.raises(AssertionError):
        await user.should_see("элемент 0")

    user.find(marker="rs-group-collapsed-demo").click()
    await user.should_see("элемент 0")


def test_flow_markers_reach_visible_line():
    """Вид потока записывается и в скрытую линию, и в видимый маршрут."""
    source = (
        ROOT / "rubik_studio/ui/pages/diagram_smart_links_v23.py"
    ).read_text(encoding="utf-8")

    assert "RS_FLOW_VISIBLE_V59" in source
    assert "for target_element in (line, route):" in source
    assert 'settings["stroke-width"] = "2.4"' in source
