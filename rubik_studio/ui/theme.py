# RS_THEME_UI_V56
"""Применение темы оформления к интерфейсу NiceGUI.

Тема — это CSS-переменные ``--rs-*`` плюс стили компонентов Quasar.
Выбор пользователя хранится в ``config.json`` и применяется при каждой
отрисовке страницы, поэтому после перезапуска всё открывается уже
в выбранной теме.

Порядок применения в ``ui.page``:

    from rubik_studio.ui.theme import apply_theme
    apply_theme()          # в начале страницы, до создания элементов

Функция идемпотентна: повторный вызов на той же странице не дублирует
``<style>``, а заменяет его.

ВАЖНО про ``shared``: стили добавляются в head конкретной страницы
(``shared=False``). Общий на всех ``shared_head_html`` для этого не
годится — это одна строка на процесс, она растёт с каждой отрисовкой и
при разных темах у разных пользователей последний записавший перекрасил
бы интерфейс всем остальным.
"""

from __future__ import annotations

from nicegui import ui

from rubik_studio.config import config
from rubik_studio.core.themes_v56 import (
    THEME_DARK,
    THEME_LIGHT,
    THEME_ORDER,
    ThemePalette,
    build_css,
    palette_for,
)

# Идентификатор тега <style>, чтобы обновлять тему без дублирования.
STYLE_ID = "rs-theme"

def current_palette() -> ThemePalette:
    """Палитра по настройкам пользователя; мусор в конфиге не ломает старт."""
    theme = config.theme if config.theme in THEME_ORDER else THEME_DARK
    try:
        return palette_for(theme, config.theme_accent, config.theme_background)
    except (ValueError, TypeError):
        # Повреждённые цвета в config.json — откат на тёмную тему.
        return palette_for(THEME_DARK)


def is_dark_theme() -> bool:
    return current_palette().name != THEME_LIGHT


def _style_block(palette: ThemePalette) -> str:
    return f'<style id="{STYLE_ID}">\n{build_css(palette)}\n</style>'


def apply_theme(palette: ThemePalette | None = None) -> ThemePalette:
    """Вставить (или заменить) стили темы на текущей странице.

    Возвращает применённую палитру — её же используют страницы, которым
    нужны отдельные цвета (например, полотно диаграммы).
    """
    active = palette or current_palette()

    # Стили страницы, а не общий буфер: у каждой вкладки своя тема.
    ui.add_head_html(_style_block(active))

    # Quasar переключает собственные тёмные токены; без этого часть
    # служебных элементов осталась бы светлой.
    if active.name == THEME_LIGHT:
        ui.dark_mode(False)
    else:
        ui.dark_mode(True)

    return active


def apply_theme_live(palette: ThemePalette | None = None) -> ThemePalette:
    """Перекрасить уже открытую страницу без перезагрузки.

    Меняет содержимое тега ``<style id="rs-theme">`` и класс тёмного
    режима на ``<body>``. Так переключатель в Настройках срабатывает
    сразу и ничего не теряет из введённого на странице.
    """
    active = palette or current_palette()

    dark = active.name != THEME_LIGHT
    css = build_css(active)

    ui.run_javascript(
        f"""
        (function () {{
            const id = {STYLE_ID!r};
            let tag = document.getElementById(id);
            if (!tag) {{
                tag = document.createElement('style');
                tag.id = id;
                document.head.appendChild(tag);
            }}
            tag.textContent = {css!r};
            document.body.classList.toggle('body--dark', {str(dark).lower()});
        }})()
        """
    )

    return active
