# RS_TEST_NOTAТION_COLORS_V57
"""Символы нотации и логотип не должны зависеть от темы оформления.

Два требования пользователя, закреплённые тестами:

1. **Цвета символов нотации меняться не должны.** Тема перекрашивает
   интерфейс вокруг поля диаграммы, но сами символы BPMN остаются
   в своих нотационных цветах, а фон поля — единый.
2. **Логотип обязателен.** Для каждой темы есть рабочий путь к файлу,
   а при пропаже файлов шапка не остаётся пустой.
"""

from __future__ import annotations

import pytest
from nicegui.testing import User

from rubik_studio.core.bpmn_shapes_v55 import COLOR
from rubik_studio.core.themes_v56 import (
    NOTATION_CANVAS_BG,
    THEME_ORDER,
    contrast_ratio,
    palette_for,
)
from rubik_studio.ui import branding

pytest_plugins = ["nicegui.testing.user_plugin"]


# ── Требование 1: нотация не зависит от темы ─────────────────────────────

@pytest.mark.parametrize("theme", THEME_ORDER)
def test_canvas_background_is_same_for_every_theme(theme):
    """Фон поля диаграммы одинаков во всех темах."""
    palette = palette_for(theme)
    assert palette.canvas_bg.upper() == NOTATION_CANVAS_BG.upper()
    assert palette.canvas_node.upper() == NOTATION_CANVAS_BG.upper()


@pytest.mark.parametrize("theme", THEME_ORDER)
def test_grid_is_readable_but_quiet(theme):
    """Сетка видна на фоне поля, но не спорит с символами."""
    palette = palette_for(theme)
    ratio = contrast_ratio(palette.canvas_grid, palette.canvas_bg)
    assert 1.05 < ratio < 2.0, f"{theme}: сетка слишком заметна или невидима ({ratio:.2f}:1)"


@pytest.mark.parametrize("theme", THEME_ORDER)
@pytest.mark.parametrize(
    "token",
    ["start", "end", "mid", "task", "subprocess", "gateway", "data", "lane"],
)
def test_symbol_colors_readable_on_notation_canvas(theme, token):
    """Любой цвет символа читается на фоне поля при любой теме.

    Цвета символов — константы модуля bpmn_shapes_v55, тема на них не
    влияет; тест страхует, что при правке фона контраст не пропадёт.
    """
    palette = palette_for(theme)
    assert contrast_ratio(COLOR[token], palette.canvas_bg) >= 3.0, (
        f"{theme}: цвет {token}={COLOR[token]} плохо виден на {palette.canvas_bg}"
    )


def test_symbol_color_table_is_not_theme_aware():
    """В модуле символов нет обращения к теме — цвета заданы константами."""
    import inspect

    from rubik_studio.core import bpmn_shapes_v55

    source = inspect.getsource(bpmn_shapes_v55)
    assert "themes_v56" not in source
    assert "palette_for" not in source
    assert "current_palette" not in source


def test_theme_does_not_redefine_symbol_colors_in_css():
    """CSS тем не переопределяет цвета символов нотации."""
    from rubik_studio.core.themes_v56 import build_css

    for theme in THEME_ORDER:
        css = build_css(palette_for(theme))
        for token in COLOR:
            if token in {"canvas", "panel", "text", "muted"}:
                continue  # это токены интерфейса, а не символов
            assert f"--rs-notation-{token}" not in css
            assert f"rs-symbol-{token}" not in css


# ── Требование 2: логотип обязателен ─────────────────────────────────────

@pytest.mark.parametrize("theme", THEME_ORDER)
def test_logo_url_exists_in_repository(theme):
    """Для каждой темы есть файл логотипа, который реально лежит на диске."""
    url = branding.header_logo_url(theme)
    filename = url.rsplit("/", 1)[-1]
    assert (branding.ASSETS / filename).exists(), f"{theme}: нет файла {filename}"


@pytest.mark.parametrize("theme", THEME_ORDER)
def test_full_logo_url_exists_in_repository(theme):
    url = branding.full_logo_url(theme)
    filename = url.rsplit("/", 1)[-1]
    assert (branding.ASSETS / filename).exists(), f"{theme}: нет файла {filename}"


def test_light_theme_uses_original_colors():
    """Светлая тема берёт оригинальные цвета, тёмные — осветлённую версию."""
    assert branding.full_logo_url("light").endswith("rubik_logo_light.png")
    for theme in ("dark", "hacker", "custom"):
        assert branding.full_logo_url(theme).endswith("rubik_logo_dark.png")


def test_header_uses_mark_without_caption():
    """В шапке 30 px — знак без надписи, иначе подпись превращается в пятно."""
    for theme in THEME_ORDER:
        assert branding.header_logo_url(theme).endswith("rubik_logo_mark.png")


def test_fallback_when_files_missing(monkeypatch, tmp_path):
    """Если папка assets пропала, остаётся исходный файл, а не пустота."""
    monkeypatch.setattr(branding, "ASSETS", tmp_path)
    for name in ("LOGO_LIGHT", "LOGO_DARK", "LOGO_MARK"):
        monkeypatch.setattr(branding, name, tmp_path / f"нет_{name}.png")

    # Исходник будто бы есть — используется он.
    source = tmp_path / "rubik_logo.png"
    source.write_bytes(b"png")
    monkeypatch.setattr(branding, "LOGO_SOURCE", source)

    assert branding.has_logo_files() is True
    assert branding.header_logo_url("hacker").endswith("rubik_logo.png")
    assert branding.full_logo_url("light").endswith("rubik_logo.png")


async def test_no_files_at_all_still_draws_a_mark(user: User, monkeypatch):
    """Худший случай: файлов нет. Логотип заменяется знаком из темы.

    Проверяется реальная отрисовка: на странице появляется элемент с
    буквой R в цветах темы, а не пустое место и не битая картинка.
    """
    from nicegui import context, ui

    monkeypatch.setattr(branding, "has_logo_files", lambda: False)

    seen: dict[str, list[str]] = {}

    @ui.page("/logo-fallback")
    def page():
        branding.logo(size=30)
        seen["html"] = [
            element.content
            for element in context.client.elements.values()
            if isinstance(element, ui.html)
        ]

    await user.open("/logo-fallback")

    marks = [html for html in seen["html"] if ">R</div>" in html]
    assert marks, "при отсутствии файлов логотип не отрисован вовсе"
    assert "var(--rs-primary)" in marks[0], "знак должен наследовать цвет темы"
