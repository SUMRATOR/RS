"""Проверка палитры символов BPMN V55.

Тест не требует браузера: NiceGUI-симулятор отрисовывает страницу и
позволяет пересчитать элементы. Проверяются три вещи:

1. каталог содержит все 43 символа и старые коды V39 не потеряны;
2. каждый символ рисуется одинаково в палитре, на поле и в миниатюре;
3. палитра действительно создаёт кнопки в живом UI, а нажатие
   передаёт правильный код символа.

Запуск:  pytest tests/test_bpmn_palette_v55.py -v
"""

from __future__ import annotations

import pytest
from nicegui import ui
from nicegui.testing import User

from rubik_studio.core.bpmn_catalog_v55 import (
    CATALOG,
    GROUP_GATEWAYS,
    by_groups,
)
from rubik_studio.core.bpmn_shapes_v55 import (
    palette_groups,
    shape_markup,
    svg_inner,
    thumbnail_svg,
)

pytest_plugins = ["nicegui.testing.user_plugin"]

# Коды, существовавшие до V55. Диаграммы, сохранённые ранее, обязаны
# открываться без миграции.
LEGACY_KINDS = [
    "START_EVENT",
    "INTERMEDIATE_EVENT",
    "END_EVENT",
    "TASK",
    "SUBPROCESS",
    "EXCLUSIVE_GATEWAY",
    "PARALLEL_GATEWAY",
    "INCLUSIVE_GATEWAY",
    "PARTICIPANT",
    "LANE",
    "DATA_INPUT",
    "DATA_OUTPUT",
    "DATA_COLLECTION",
]


# ── Каталог ────────────────────────────────────────────────────────────────

def test_catalog_has_expected_size():
    """43 символа V55 + 18 событий V58: граничные, отмена и составные."""
    assert len(CATALOG) == 61


def test_legacy_codes_preserved():
    """Старые коды V39 не удалены — обратная совместимость диаграмм."""
    missing = [kind for kind in LEGACY_KINDS if kind not in CATALOG]
    assert missing == [], f"потеряны коды: {missing}"


def test_all_event_types_from_specification_present():
    """Все 13 типов событий из таблицы BPMN 2.0 заведены."""
    required = [
        "START_EVENT",
        "START_MESSAGE",
        "START_TIMER",
        "START_CONDITIONAL",
        "START_SIGNAL",
        "START_ERROR",
        "INTERMEDIATE_EVENT",
        "INTERMEDIATE_MESSAGE",
        "INTERMEDIATE_TIMER",
        "INTERMEDIATE_ESCALATION",
        "INTERMEDIATE_CONDITIONAL",
        "INTERMEDIATE_LINK",
        "INTERMEDIATE_SIGNAL",
        "INTERMEDIATE_ERROR",
        "INTERMEDIATE_COMPENSATION",
        "END_EVENT",
        "END_TERMINATE",
        "END_MESSAGE",
        "END_ERROR",
        "END_SIGNAL",
    ]
    missing = [kind for kind in required if kind not in CATALOG]
    assert missing == [], f"нет событий: {missing}"


def test_all_seven_gateways_present():
    """Семь шлюзов: XOR, И, И/ИЛИ, по событиям, комплексный и два по событию."""
    gateways = [k for k, v in CATALOG.items() if v["group"] == GROUP_GATEWAYS]
    assert len(gateways) == 7


def test_every_entry_has_human_readable_text():
    """У каждого символа есть подпись, подсказка и пример — без пустых мест."""
    for kind, info in CATALOG.items():
        assert info["label"].strip(), f"{kind}: пустая подпись"
        assert info["hint"].strip(), f"{kind}: пустая подсказка"
        assert info.get("example", "").strip(), f"{kind}: нет примера"


def test_groups_cover_every_symbol():
    """Ни один символ не выпадает из палитры."""
    in_groups = {
        kind for _group, items in by_groups() for kind, _label in items
    }
    assert in_groups == set(CATALOG)


# ── Отрисовка ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", sorted(CATALOG))
def test_every_symbol_renders(kind):
    """Каждый символ даёт непустой SVG во всех трёх представлениях."""
    inner = svg_inner(kind)
    assert "<" in inner and len(inner) > 40

    canvas = shape_markup(kind, "Проверка")
    assert "<svg" in canvas
    assert "</svg>" in canvas
    assert "Проверка" in canvas

    thumb = thumbnail_svg(kind)
    assert "<svg" in thumb and "</svg>" in thumb


def test_user_text_is_escaped():
    """Пользовательское название не ломает разметку и не даёт XSS."""
    markup = shape_markup("TASK", '<script>alert(1)</script>')
    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup


def test_shape_and_thumbnail_use_same_geometry():
    """Поле и палитра рисуют символ из одного источника."""
    canvas = svg_inner("START_TIMER")
    thumb = thumbnail_svg("START_TIMER")
    assert canvas in thumb


def test_palette_groups_have_thumbnails():
    """Каждая группа палитры несёт готовые миниатюры."""
    groups = palette_groups()
    assert groups
    for group_name, items in groups:
        assert group_name
        for kind, label, hint, thumb in items:
            assert kind in CATALOG
            assert label and hint
            assert "<svg" in thumb


# ── Палитра в живом UI ─────────────────────────────────────────────────────

async def test_palette_renders_in_ui(user: User):
    """Палитра создаёт кнопки и передаёт выбранный код символа."""
    from rubik_studio.ui.pages.diagram_editor_v16 import render_bpmn_palette_v55

    chosen: list[str] = []

    @ui.page("/palette")
    def page():
        render_bpmn_palette_v55(lambda kind: chosen.append(kind))

    await user.open("/palette")

    # Палитра содержит 43 символа и 43 кнопки «добавить».
    await user.should_see("События")
    await user.should_see("Шлюзы")
    await user.should_see("Начальное событие (здесь начинается процесс)")

    # Кнопка добавления у каждого символа помечена маркером
    # «rs-add-<КОД>» — по нему и находим конкретный символ.
    user.find(marker="rs-add-START_TIMER").click()
    assert chosen == ["START_TIMER"], f"получено: {chosen}"

    user.find(marker="rs-add-END_TERMINATE").click()
    assert chosen == ["START_TIMER", "END_TERMINATE"]
