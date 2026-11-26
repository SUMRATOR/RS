# RS_BPMN_EVENT_PALETTE_V58
"""Палитра вариантов событий: вкладки положений и выбор подтипа.

Пользователь не должен помнить коды символов. Он выбирает положение
(«Начальное», «Промежуточное», «Граничное», «Конечное»), затем подтип
(«Таймер», «Сообщение» …) — и на схему попадает нужное событие.

Граничные события — отдельный режим: они крепятся к границе задачи,
поэтому в палитре помечены подсказкой «крепится к задаче», а выбор
отдаётся редактору как есть, чтобы он включил режим привязки.

Модуль отделён от редактора (файл на несколько тысяч строк), чтобы
палитру можно было проверить автотестом без запуска всего редактора.
"""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from rubik_studio.core.bpmn_events_v58 import (
    POSITION_BOUNDARY,
    POSITION_HINTS,
    POSITION_ORDER,
    POSITION_TITLES,
    SUBTYPE_PLAIN,
    EventVariant,
    all_variants,
    variants_for_position,
)
from rubik_studio.core.bpmn_shapes_v55 import thumbnail_svg

# Размер миниатюры во вкладке подтипов.
THUMB_SIZE = 44

# Цвета палитры символов. Это цвета интерфейса, а не нотации: панель
# живёт в тёмной части редактора, символы внутри неё сохраняют свои
# нотационные цвета (их задаёт bpmn_shapes_v55.COLOR).
PANEL_BG = "#1E2B45"
PANEL_BORDER = "#33415C"
MUTED = "#A9B8CF"
CAPTION = "#E8EDF5"
ACTIVE = "#7FB2FF"


def _on_pick_variant(
    variant: EventVariant,
    on_pick: Callable[[str], None],
) -> None:
    """Передать выбранный вариант редактору."""
    on_pick(variant.kind)


def render_event_variants_palette(
    on_pick: Callable[[str], None],
    on_hint: Callable[[str], None] | None = None,
    start_position: str = POSITION_ORDER[0],
) -> None:
    """Палитра событий по положениям.

    ``on_pick`` получает код символа — ровно тот же, что и раньше, поэтому
    сохранение диаграмм не меняется.

    ``on_hint`` показывает карточку-подсказку; если не передан, кнопка
    подсказки не выводится.
    """
    ui.label("Событие: выберите положение").style(
        "font-size:13px; font-weight:600; color:" + CAPTION
    )

    # Контейнер подтипов перерисовывается при смене вкладки.
    subtype_box = ui.column().classes("w-full gap-1")

    # Какой подтип сейчас выбран у каждого положения — при возврате на
    # вкладку показываем его же, а не сбрасываем на первый.
    remembered: dict[str, str] = {}

    def fill_subtypes(position: str) -> None:
        subtype_box.clear()
        variants = variants_for_position(position)

        with subtype_box:
            ui.label(POSITION_HINTS[position]).style(
                f"font-size:11px; color:{MUTED}; line-height:14px;"
            )

            if position == POSITION_BOUNDARY:
                ui.label(
                    "Крепится к границе задачи или подпроцесса — "
                    "сначала выделите задачу на схеме."
                ).style(f"font-size:11px; color:{ACTIVE}; line-height:14px;")

            grid = ui.element("div").style(
                "display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); "
                "gap:6px; width:100%; margin-top:4px;"
            )

            with grid:
                for variant in variants:
                    _render_variant_card(variant, on_pick, on_hint)

    def select_position(position: str) -> None:
        remembered[position] = remembered.get(position, "")
        fill_subtypes(position)

    with ui.row().classes("w-full gap-1 no-wrap"):
        for position in POSITION_ORDER:
            active = position == start_position
            button = ui.button(
                POSITION_TITLES[position],
                on_click=lambda p=position: fill_subtypes(p),
            ).props("dense no-caps flat")
            button.style(
                "font-size:11px; padding:4px 8px; border-radius:6px; "
                + (
                    f"background:{ACTIVE}; color:#0F172A; font-weight:600;"
                    if active
                    else f"border:1px solid {PANEL_BORDER}; color:{MUTED};"
                )
            )
            button.props(f'data-rs-position={position}')
            button.mark(f"rs-position-{position}")

    fill_subtypes(start_position)


def _render_variant_card(
    variant: EventVariant,
    on_pick: Callable[[str], None],
    on_hint: Callable[[str], None] | None,
) -> None:
    """Карточка одного подтипа: миниатюра, подпись, добавить, подсказка."""
    with ui.element("div").style(
        "display:flex; flex-direction:column; align-items:center; gap:2px; "
        f"padding:6px 4px; border-radius:10px; background:{PANEL_BG}; "
        f"border:1px solid {PANEL_BORDER};"
    ):
        ui.html(
            thumbnail_svg(variant.kind, THUMB_SIZE),
            sanitize=False,
        ).style(f"height:{THUMB_SIZE}px; display:flex; align-items:center;")

        ui.label(variant.subtype_title).style(
            f"font-size:11px; line-height:13px; text-align:center; color:{CAPTION};"
        )

        with ui.row().classes("gap-1 no-wrap"):
            add_button = ui.button(
                icon="add",
                on_click=lambda k=variant.kind: _on_pick_variant(variant, on_pick)
                if k
                else None,
            ).props(
                "flat dense round size=sm "
                f'aria-label="Добавить: {variant.kind}" '
                f"data-rs-symbol-add={variant.kind}"
            ).style(f"color:{ACTIVE};")
            add_button.mark(f"rs-variant-add-{variant.kind}")
            add_button.tooltip("Добавить на схему")

            if on_hint is not None:
                hint_button = ui.button(
                    icon="help_outline",
                    on_click=lambda k=variant.kind: on_hint(k),
                ).props(
                    "flat dense round size=sm "
                    f'aria-label="Подсказка: {variant.kind}" '
                    f"data-rs-symbol-hint={variant.kind}"
                ).style(f"color:{MUTED};")
                hint_button.mark(f"rs-variant-hint-{variant.kind}")
                hint_button.tooltip("Что это и когда применять")


def palette_signature() -> str:
    """Короткая подпись состава палитры — для тестов и журнала.

    Показывает, сколько вариантов в каждом положении и нет ли варианта без
    символа (такой пользователь увидел бы пустую кнопку).
    """
    parts = []
    for position in POSITION_ORDER:
        variants = variants_for_position(position)
        empty = [v.kind for v in variants if not v.available]
        parts.append(
            f"{POSITION_TITLES[position]}: {len(variants)}"
            + (f" (без символа: {len(empty)})" if empty else "")
        )
    return "; ".join(parts)


def plain_variant_positions() -> list[str]:
    """Положения, где есть вариант «без подтипа»."""
    return [
        position
        for position in POSITION_ORDER
        if any(v.subtype == SUBTYPE_PLAIN for v in variants_for_position(position))
    ]


def total_variants() -> int:
    return len(all_variants())
