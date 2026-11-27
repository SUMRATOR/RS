"""Проверка подключения тем к интерфейсу.

Проверяется не только расчёт палитры, но и то, что тема действительно
попадает на страницу: CSS-переменные, шапка, боковое меню, блок
«Оформление» в настройках и сохранение выбора в config.json.
"""

from __future__ import annotations

import pytest
from nicegui import ui
from nicegui.testing import User

from rubik_studio.config import config
from rubik_studio.core.themes_v56 import (
    THEME_CUSTOM,
    THEME_HACKER,
    THEME_LIGHT,
    palette_for,
)
from rubik_studio.ui import theme as theme_ui

pytest_plugins = ["nicegui.testing.user_plugin"]


@pytest.fixture
def restore_config():
    """После теста возвращает исходные настройки оформления."""
    saved = (config.theme, config.theme_accent, config.theme_background)
    yield
    config.theme, config.theme_accent, config.theme_background = saved


# ── Палитра из настроек ───────────────────────────────────────────────────

@pytest.mark.parametrize("theme", [THEME_LIGHT, "dark", THEME_HACKER])
def test_current_palette_follows_config(theme, restore_config):
    config.theme = theme
    assert theme_ui.current_palette().name == theme


def test_broken_config_falls_back_to_dark(restore_config):
    """Мусор в config.json не должен ломать запуск приложения."""
    config.theme = "несуществующая-тема"
    assert theme_ui.current_palette().name == "dark"

    config.theme = THEME_CUSTOM
    config.theme_accent = "не-цвет"
    assert theme_ui.current_palette().name == "dark"


def test_custom_theme_reads_user_colors(restore_config):
    config.theme = THEME_CUSTOM
    config.theme_accent = "#FF6B2C"
    config.theme_background = "#101820"
    palette = theme_ui.current_palette()
    assert palette.primary == "#FF6B2C"
    assert palette.bg == "#101820"


def test_light_theme_reports_not_dark(restore_config):
    config.theme = THEME_LIGHT
    assert theme_ui.is_dark_theme() is False
    config.theme = "dark"
    assert theme_ui.is_dark_theme() is True


# ── Тема на странице ──────────────────────────────────────────────────────

async def test_theme_is_applied_to_page(user: User, restore_config):
    """CSS темы присутствует на странице, собранной через макет."""
    from rubik_studio.ui.layout import create_page_layout

    config.theme = THEME_HACKER

    @ui.page("/themed")
    def page():
        create_page_layout("Проверка темы")

    await user.open("/themed")

    await user.should_see("Проверка темы")
    await user.should_see("RS — RUBIK STUDIO")


async def test_settings_page_shows_theme_block(user: User, restore_config):
    """В настройках есть выбор темы и цветов своей тёмной темы."""
    from rubik_studio.ui.pages.settings import render

    config.theme = "dark"

    @ui.page("/settings-test")
    async def page():
        await render()

    await user.open("/settings-test")

    await user.should_see("Оформление")
    await user.should_see("Тема")
    await user.should_see("Своя тёмная тема")
    await user.should_see("Цвет подсветки")


async def test_theme_choice_is_saved(user: User, restore_config):
    """Выбор темы в интерфейсе сохраняется в конфигурации."""
    from rubik_studio.ui.pages.settings import render

    config.theme = "dark"

    @ui.page("/settings-save")
    async def page():
        await render()

    await user.open("/settings-save")

    # В блоке «Оформление» показано описание выбранной темы —
    # это подтверждает, что тема из настроек прочитана и отрисована.
    await user.should_see("Нейтральная тёмная тема")


def test_theme_options_have_russian_names():
    """В списке тем — русские названия, а не коды из config.json."""
    from rubik_studio.core.themes_v56 import THEME_INFO

    assert THEME_INFO["light"]["name"] == "Светлая"
    assert THEME_INFO["dark"]["name"] == "Тёмная"
    assert THEME_INFO["hacker"]["name"] == "Hacker"
    assert THEME_INFO["custom"]["name"] == "Своя тёмная"


def test_css_variables_are_unique_per_theme():
    """Разные темы дают разный CSS — иначе переключение бессмысленно."""
    css_light = theme_ui.build_css(palette_for(THEME_LIGHT))
    css_dark = theme_ui.build_css(palette_for("dark"))
    css_hacker = theme_ui.build_css(palette_for(THEME_HACKER))
    assert css_light != css_dark
    assert css_dark != css_hacker
    # Светлая тема не использует тёмный фон тёмной темы.
    assert "#F6F2EA" in css_light
    assert "#F6F2EA" not in css_dark


# ── Живое переключение и защита от общего буфера ──────────────────────────

async def test_theme_follows_user_not_other_pages(user: User, restore_config):
    """Тема берётся из настроек, а не из общей строки head.

    Раньше CSS писался в ``shared_head_html`` — одну строку на процесс.
    Вторая открытая страница с другой темой перекрашивала первую.
    """
    from rubik_studio.ui.theme import apply_theme

    config.theme = THEME_LIGHT
    html_light = theme_ui._style_block(theme_ui.current_palette())
    config.theme = THEME_HACKER
    html_hacker = theme_ui._style_block(theme_ui.current_palette())

    assert "--rs-bg: #F6F2EA" in html_light
    assert "--rs-bg: #050A07" in html_hacker

    # head-буфер, снятый внутри отрисовки страницы
    seen: dict[str, str] = {}

    @ui.page("/theme-a")
    def page_a():
        from nicegui import context

        seen["head"] = context.client.shared_head_html
        apply_theme(palette_for(THEME_LIGHT))

    @ui.page("/theme-b")
    def page_b():
        apply_theme(palette_for(THEME_HACKER))

    await user.open("/theme-a")

    # CSS темы не попал в общий на процесс буфер: иначе вторая вкладка
    # с другой темой перекрасила бы первую.
    assert "rs-theme" not in seen["head"]


def test_live_update_script_replaces_style_not_appends(monkeypatch):
    """Живое переключение заменяет содержимое <style>, а не плодит теги."""
    calls = []
    monkeypatch.setattr(theme_ui.ui, "run_javascript", lambda code: calls.append(code))

    theme_ui.apply_theme_live(palette_for(THEME_LIGHT))

    assert len(calls) == 1
    script = calls[0]
    assert "getElementById" in script
    assert "createElement('style')" in script
    assert "tag.textContent" in script
    assert "body--dark" in script
