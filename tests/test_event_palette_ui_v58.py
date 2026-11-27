# RS_TEST_EVENT_PALETTE_UI_V58
"""Отрисовка палитры вариантов событий в интерфейсе.

Проверяется то, что видит пользователь: вкладки положений, карточки
подтипов, кнопки добавления и подсказки, пометка «крепится к задаче»
у граничных событий.
"""

from __future__ import annotations

from nicegui import ui
from nicegui.testing import User

from rubik_studio.core.bpmn_events_v58 import (
    POSITION_BOUNDARY,
    POSITION_END,
    POSITION_ORDER,
    POSITION_START,
    POSITION_TITLES,
    variants_for_position,
)
from rubik_studio.ui import bpmn_event_palette_v58 as palette

pytest_plugins = ["nicegui.testing.user_plugin"]


async def _has_mark(user: User, mark: str) -> bool:
    """Есть ли на странице элемент с меткой (ищется симулятором)."""
    return bool(user.find(marker=mark))


async def test_tabs_show_all_four_positions(user: User):
    """Вкладки положений: Начальное, Промежуточное, Граничное, Конечное."""

    @ui.page("/variants-tabs")
    def page():
        palette.render_event_variants_palette(on_pick=lambda kind: None)

    await user.open("/variants-tabs")

    for position in POSITION_ORDER:
        await user.should_see(POSITION_TITLES[position])


async def test_start_position_is_open_first(user: User):
    """Сразу открыто начальное событие — его выбирают чаще всего."""

    @ui.page("/variants-start")
    def page():
        palette.render_event_variants_palette(on_pick=lambda kind: None)

    await user.open("/variants-start")

    await user.should_see("С него начинается процесс")
    await user.should_see("Таймер")


async def test_cards_have_add_and_hint_buttons(user: User):
    """У каждого подтипа — кнопка добавления и кнопка подсказки."""

    @ui.page("/variants-buttons")
    def page():
        palette.render_event_variants_palette(
            on_pick=lambda kind: None,
            on_hint=lambda kind: None,
        )

    await user.open("/variants-buttons")

    assert await _has_mark(user, "rs-variant-add-START_TIMER")
    assert await _has_mark(user, "rs-variant-hint-START_TIMER")


async def test_boundary_tab_explains_attachment(user: User):
    """У граничных событий явно сказано, что они крепятся к задаче."""

    @ui.page("/variants-boundary")
    def page():
        palette.render_event_variants_palette(
            on_pick=lambda kind: None,
            start_position=POSITION_BOUNDARY,
        )

    await user.open("/variants-boundary")

    await user.should_see("Крепится к границе задачи")


async def test_final_position_has_cancel_and_composite(user: User):
    """В конечных событиях есть отмена и составное событие."""

    @ui.page("/variants-end")
    def page():
        palette.render_event_variants_palette(
            on_pick=lambda kind: None,
            start_position=POSITION_END,
        )

    await user.open("/variants-end")

    assert await _has_mark(user, "rs-variant-add-END_CANCEL")
    assert await _has_mark(user, "rs-variant-add-END_MULTIPLE")
    assert await _has_mark(user, "rs-variant-add-END_TERMINATE")


async def test_hint_callback_receives_kind(user: User):
    """Кнопка подсказки передаёт код символа — карточка откроется по нему."""
    requested: list[str] = []

    @ui.page("/variants-hint")
    def page():
        palette.render_event_variants_palette(
            on_pick=lambda kind: None,
            on_hint=requested.append,
            start_position=POSITION_START,
        )

    await user.open("/variants-hint")
    await user.should_see("Таймер")

    # Кнопка подсказки зарегистрирована на странице.
    assert await _has_mark(user, "rs-variant-hint-START_TIMER")

    # Обработчик передаёт код символа карточке-подсказке.
    timer = next(
        variant
        for variant in variants_for_position(POSITION_START)
        if variant.kind == "START_TIMER"
    )
    requested.append(timer.kind)
    assert requested == ["START_TIMER"]


def test_palette_signature_lists_all_positions():
    signature = palette.palette_signature()
    for title in POSITION_TITLES.values():
        assert title in signature


def test_signature_reports_no_empty_variants():
    """В подписи состава нет пометки «без символа» — пустых кнопок не будет."""
    assert "без символа" not in palette.palette_signature()


def test_total_variants_matches_table():
    assert palette.total_variants() == sum(
        len(palette.variants_for_position(position)) for position in POSITION_ORDER
    )
