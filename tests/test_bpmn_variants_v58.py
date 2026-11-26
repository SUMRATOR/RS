# RS_TEST_BPMN_VARIANTS_V58
"""Палитра вариантов событий и 18 новых символов (V58).

Проверяется три вещи:

1. таблица совместимости «положение + подтип» полна и без пустых мест;
2. каждый вариант нарисован — пользователь не увидит пустую кнопку;
3. старые коды и подписи V55 не изменились.
"""

from __future__ import annotations

import pytest

from rubik_studio.core.bpmn_catalog_v55 import CATALOG
from rubik_studio.core.bpmn_events_v58 import (
    COMPATIBILITY,
    POSITION_BOUNDARY,
    POSITION_END,
    POSITION_INTERMEDIATE,
    POSITION_ORDER,
    POSITION_START,
    SUBTYPE_CANCEL,
    SUBTYPE_ERROR,
    SUBTYPE_MESSAGE,
    SUBTYPE_MULTIPLE,
    SUBTYPE_PARALLEL_MULTIPLE,
    SUBTYPE_PLAIN,
    SUBTYPE_TIMER,
    EventVariant,
    all_variants,
    boundary_kinds,
    catch_or_throw,
    is_boundary,
    missing_kinds,
    position_of_kind,
    subtype_of_kind,
    variant_for,
    variants_for_position,
)
from rubik_studio.core.bpmn_shapes_v55 import (
    _EVENT_SPEC,
    COLOR,
    thumbnail_svg,
)
from rubik_studio.core.themes_v56 import NOTATION_CANVAS_BG, contrast_ratio

# ── Состав таблицы ────────────────────────────────────────────────────────

def test_positions_in_expected_order():
    assert POSITION_ORDER == (
        POSITION_START,
        POSITION_INTERMEDIATE,
        POSITION_BOUNDARY,
        POSITION_END,
    )


@pytest.mark.parametrize("position", POSITION_ORDER)
def test_every_position_has_variants(position):
    assert variants_for_position(position), f"{position}: нет ни одного варианта"


def test_nothing_is_declared_but_missing():
    """У каждого варианта есть нарисованный символ — иначе была бы пустая кнопка."""
    assert missing_kinds() == []


def test_every_variant_kind_is_in_catalog():
    for variant in all_variants():
        assert variant.kind in CATALOG, f"{variant.kind} нет в каталоге"


def test_every_event_variant_is_drawn():
    for variant in all_variants():
        assert variant.kind in _EVENT_SPEC, f"{variant.kind} не рисуется"


def test_no_duplicate_kinds_in_compatibility_table():
    kinds = [kind for mapping in COMPATIBILITY.values() for kind in mapping.values()]
    assert len(kinds) == len(set(kinds)), "один код приписан двум вариантам"


# ── Новые символы V58 ─────────────────────────────────────────────────────

NEW_KINDS = (
    "START_MULTIPLE",
    "START_PARALLEL_MULTIPLE",
    "INTERMEDIATE_MULTIPLE",
    "INTERMEDIATE_PARALLEL_MULTIPLE",
    "END_ESCALATION",
    "END_COMPENSATION",
    "END_CANCEL",
    "END_MULTIPLE",
    "BOUNDARY_MESSAGE",
    "BOUNDARY_TIMER",
    "BOUNDARY_ESCALATION",
    "BOUNDARY_CONDITIONAL",
    "BOUNDARY_ERROR",
    "BOUNDARY_CANCEL",
    "BOUNDARY_COMPENSATION",
    "BOUNDARY_SIGNAL",
    "BOUNDARY_MULTIPLE",
    "BOUNDARY_PARALLEL_MULTIPLE",
)


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_new_symbol_has_full_description(kind):
    """Новый символ описан так же подробно, как символы V55."""
    info = CATALOG[kind]
    assert info["label"]
    assert info["hint"]
    assert info["example"]
    assert info["group"] == "События"


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_new_symbol_has_thumbnail(kind):
    svg = thumbnail_svg(kind, 40)
    assert svg.startswith("<svg")
    assert "aria-hidden" in svg


def test_all_eighteen_new_symbols_present():
    assert len(NEW_KINDS) == 18
    for kind in NEW_KINDS:
        assert CATALOG[kind]["legacy"] is False


# ── Граничные события ─────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", boundary_kinds())
def test_boundary_event_is_dashed(kind):
    """Граничное событие рисуется пунктиром — так принято в BPMN."""
    assert 'stroke-dasharray' in thumbnail_svg(kind, 40)


def test_boundary_has_no_plain_variant():
    """У граничных нет «пустого» варианта: им нужна причина."""
    assert not any(
        variant.subtype == SUBTYPE_PLAIN for variant in variants_for_position(POSITION_BOUNDARY)
    )


def test_boundary_detection():
    assert is_boundary("BOUNDARY_TIMER") is True
    assert is_boundary("INTERMEDIATE_TIMER") is False


def test_boundary_events_have_flag_in_catalog():
    for kind in boundary_kinds():
        assert CATALOG[kind].get("boundary") is True


def test_boundary_color_is_readable():
    ratio = contrast_ratio(COLOR["boundary"], NOTATION_CANVAS_BG)
    assert ratio >= 3.0, f"граничные события плохо видны на фоне нотации ({ratio:.2f}:1)"


# ── Составные события ─────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "position, subtype",
    [
        (POSITION_START, SUBTYPE_MULTIPLE),
        (POSITION_START, SUBTYPE_PARALLEL_MULTIPLE),
        (POSITION_INTERMEDIATE, SUBTYPE_MULTIPLE),
        (POSITION_INTERMEDIATE, SUBTYPE_PARALLEL_MULTIPLE),
        (POSITION_BOUNDARY, SUBTYPE_MULTIPLE),
        (POSITION_BOUNDARY, SUBTYPE_PARALLEL_MULTIPLE),
        (POSITION_END, SUBTYPE_MULTIPLE),
    ],
)
def test_composite_event_exists(position, subtype):
    variant = variant_for(position, subtype)
    assert variant is not None
    assert variant.available


# ── Отмена ────────────────────────────────────────────────────────────────

def test_cancel_events_exist_only_where_bpmn_allows():
    assert variant_for(POSITION_BOUNDARY, SUBTYPE_CANCEL) is not None
    assert variant_for(POSITION_END, SUBTYPE_CANCEL) is not None
    # Отмены начального события в нотации нет.
    assert variant_for(POSITION_START, SUBTYPE_CANCEL) is None


# ── Названия и обратный поиск ─────────────────────────────────────────────

def test_variant_title_is_human_readable():
    variant = variant_for(POSITION_INTERMEDIATE, SUBTYPE_TIMER)
    assert variant is not None
    assert variant.title == "Промежуточное: Таймер"


def test_plain_variant_title_has_no_subtype():
    variant = variant_for(POSITION_START, SUBTYPE_PLAIN)
    assert variant is not None
    assert variant.title == "Начальное"


def test_reverse_lookup():
    assert position_of_kind("BOUNDARY_TIMER") == POSITION_BOUNDARY
    assert subtype_of_kind("BOUNDARY_TIMER") == SUBTYPE_TIMER
    assert position_of_kind("НЕТ_ТАКОГО") is None


def test_label_comes_from_catalog():
    variant = variant_for(POSITION_BOUNDARY, SUBTYPE_ERROR)
    assert variant is not None
    assert variant.label == CATALOG["BOUNDARY_ERROR"]["label"]


def test_event_variant_is_immutable():
    variant = EventVariant(POSITION_START, SUBTYPE_TIMER, "START_TIMER")
    with pytest.raises(Exception):
        variant.kind = "OTHER"


# ── Поведение «поймать / выбросить» ───────────────────────────────────────

def test_intermediate_timer_is_catch():
    assert catch_or_throw(POSITION_INTERMEDIATE, SUBTYPE_TIMER) == "catch"


def test_intermediate_link_is_throw():
    assert catch_or_throw(POSITION_INTERMEDIATE, "link") == "throw"


def test_other_positions_have_no_catch_throw():
    assert catch_or_throw(POSITION_START, SUBTYPE_MESSAGE) == ""
    assert catch_or_throw(POSITION_BOUNDARY, SUBTYPE_TIMER) == ""


# ── Совместимость с V55 ───────────────────────────────────────────────────

def test_legacy_codes_still_present():
    for kind in (
        "START_EVENT",
        "INTERMEDIATE_EVENT",
        "END_EVENT",
        "TASK",
        "EXCLUSIVE_GATEWAY",
    ):
        assert kind in CATALOG
        assert kind in _EVENT_SPEC or CATALOG[kind]["group"] != "События"


def test_old_event_labels_unchanged():
    """Подписи V55 не переписаны — их диктуют на занятии."""
    assert CATALOG["START_EVENT"]["label"].startswith("Начальное событие")
    assert CATALOG["END_EVENT"]["label"].startswith("Конечное событие")


def test_boundary_uses_single_color_for_all_types():
    """У граничных событий цвет один: положение у них всегда «граничное».

    Тип различается пиктограммой, а не цветом — иначе «таймер» и «ошибка»
    выглядели бы как события разных положений.
    """
    from rubik_studio.core.bpmn_shapes_v55 import _event_svg

    for kind in boundary_kinds():
        svg = _event_svg(kind)
        # Контур рисуется только цветом граничных событий; остальные
        # штрихи — это пиктограмма внутри, она цвета текста.
        assert f'stroke="{COLOR["boundary"]}"' in svg
        assert f'stroke="{COLOR["start"]}"' not in svg
        assert f'stroke="{COLOR["end"]}"' not in svg
        assert f'stroke="{COLOR["mid"]}"' not in svg
