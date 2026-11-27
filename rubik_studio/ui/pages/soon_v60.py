# RS_SOON_PAGES_V60
"""Разделы, которые ещё не готовы: страница вместо ошибки 404.

Раньше пункты меню «Моделирование», «Process Mining» и «Задачи и
процессы» вели на несуществующие адреса: пользователь нажимал и получал
404 — это выглядело как поломка приложения.

Теперь по этим адресам открывается обычная страница приложения с
шапкой, меню и темой. На ней честно написано, что раздел в разработке,
что уже есть и что будет дальше. Значок «?» из системы подсказок
показывает, что это «возможная ошибка» — то есть место, куда ещё рано
идти за результатом.
"""

from __future__ import annotations

from nicegui import ui

from rubik_studio.ui.hints_v60 import KIND_WARNING, hint_icon, info_badge
from rubik_studio.ui.layout import create_page_layout, empty_state

# Описание неготовых разделов: что это, что уже есть, что дальше.
SECTIONS = {
    "modeler": {
        "title": "Моделирование",
        "summary": "Универсальные редакторы схем: VAD, дерево целей, EPC.",
        "ready": (
            "Готов редактор BPMN-диаграмм: он открывается из «Репозитория» — "
            "создайте объект-модель и нажмите «Открыть»."
        ),
        "next": (
            "Дальше по плану: универсальное полотно для VAD, дерево целей "
            "и EPC. Они используют то же полотно, что и BPMN."
        ),
        "action": ("Открыть репозиторий", "/repository"),
    },
    "mining": {
        "title": "Process Mining",
        "summary": "Анализ журналов событий: карта процесса и отклонения.",
        "ready": (
            "Пока не реализовано. Основа — те же диаграммы, что уже "
            "строятся в BPMN."
        ),
        "next": (
            "По плану: загрузка CSV, карта частот (DFG), проверка "
            "соответствия фактического процесса модели."
        ),
        "action": ("Вернуться на главную", "/"),
    },
    "bpms": {
        "title": "Задачи и процессы",
        "summary": "Исполнение процессов: задачи, исполнители, сроки.",
        "ready": (
            "Пока не реализовано. Модели процессов уже можно описывать и "
            "рисовать в BPMN."
        ),
        "next": (
            "По плану: задачи по элементам процесса, назначение "
            "исполнителей, контроль сроков."
        ),
        "action": ("Открыть базы моделирования", "/modeling-databases"),
    },
}


def render_soon(section: str) -> None:
    """Показать страницу неготового раздела."""
    info = SECTIONS.get(section)

    if info is None:
        content = create_page_layout("Раздел не найден")
        with content:
            ui.label("Такого раздела нет.").classes("text-lg")
            ui.button(
                "На главную", on_click=lambda: ui.navigate.to("/")
            ).props("flat")
        return

    content = create_page_layout(info["title"])

    with content:
        with ui.row().classes("items-center gap-2 no-wrap"):
            # «?» — возможная ошибка: сюда идти за результатом пока рано.
            hint_icon(
                "Раздел ещё в разработке. Пункт меню оставлен, чтобы был "
                "виден план, но результатов здесь пока нет.",
                KIND_WARNING,
            )
            ui.label("Раздел в разработке").classes("text-lg font-semibold")

        ui.label(info["summary"]).classes("text-sm")

        with ui.card().classes("w-full"):
            ui.label("Что уже готово").classes("text-base font-semibold")
            ui.label(info["ready"]).classes("text-sm")

        with ui.card().classes("w-full"):
            ui.label("Что будет дальше").classes("text-base font-semibold")
            ui.label(info["next"]).classes("text-sm")

        label, path = info["action"]
        ui.button(label, on_click=lambda: ui.navigate.to(path))

        empty_state(
            "engineering",
            "Раздел появится в следующих версиях. Пока используйте "
            "готовые: репозиторий объектов и BPMN-диаграммы.",
        )

        with ui.row().classes("items-center gap-2 no-wrap"):
            info_badge(
                "Пункты меню, ведущие в разработку, помечены значком «?». "
                "Он означает «возможная ошибка»: то, что ещё не работает, "
                "видно заранее.",
            )
            ui.label("Про обозначения").classes("text-sm")
