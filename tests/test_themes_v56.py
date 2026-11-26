"""Проверка тем оформления V56.

Проверяется то, что можно проверить без браузера:

* все четыре темы дают полный набор цветовых токенов;
* текст читается: контраст не ниже 4.5:1 (WCAG AA);
* светлая тема действительно тёплая, а не сине-белая;
* пользовательская тема корректно выводит палитру из двух цветов;
* некорректный цвет не ломает приложение, а даёт понятную ошибку.

Запуск: pytest tests/test_themes_v56.py -v
"""

from __future__ import annotations

import pytest

from rubik_studio.core.themes_v56 import (
    THEME_CUSTOM,
    THEME_DARK,
    THEME_HACKER,
    THEME_INFO,
    THEME_LIGHT,
    THEME_ORDER,
    ThemePalette,
    build_css,
    contrast_ratio,
    custom_palette,
    mix,
    palette_for,
    parse_hex,
    readable_text_color,
)

REQUIRED_TOKENS = (
    "bg",
    "surface",
    "surface_alt",
    "border",
    "text",
    "text_muted",
    "primary",
    "primary_text",
    "canvas_bg",
    "canvas_grid",
    "canvas_node",
    "canvas_edge",
)


@pytest.mark.parametrize("theme", THEME_ORDER)
def test_every_theme_has_all_tokens(theme):
    palette = palette_for(theme)
    assert isinstance(palette, ThemePalette)
    for token in REQUIRED_TOKENS:
        value = getattr(palette, token)
        assert value, f"{theme}: пустой токен {token}"
        assert value.startswith("#") and len(value) == 7, f"{theme}.{token} = {value}"


@pytest.mark.parametrize("theme", THEME_ORDER)
def test_body_text_contrast_is_accessible(theme):
    """Основной текст на фоне — не ниже 4.5:1 (WCAG AA)."""
    palette = palette_for(theme)
    ratio = contrast_ratio(palette.text, palette.bg)
    assert ratio >= 4.5, f"{theme}: контраст текста {ratio:.2f} < 4.5"


@pytest.mark.parametrize("theme", THEME_ORDER)
def test_muted_text_is_readable(theme):
    """Пояснения и подписи — не ниже 4.5:1, они несут смысл, а не декор."""
    palette = palette_for(theme)
    ratio = contrast_ratio(palette.text_muted, palette.bg)
    assert ratio >= 4.5, f"{theme}: контраст подписей {ratio:.2f} < 4.5"


@pytest.mark.parametrize("theme", THEME_ORDER)
def test_text_on_primary_button_is_readable(theme):
    """Текст на главной кнопке читается."""
    palette = palette_for(theme)
    ratio = contrast_ratio(palette.primary_text, palette.primary)
    assert ratio >= 4.4, f"{theme}: текст на кнопке {ratio:.2f} < 4.4"


@pytest.mark.parametrize("theme", THEME_ORDER)
def test_border_is_visible_but_not_loud(theme):
    """Рамка отличается от фона: видна, но не спорит с содержимым."""
    palette = palette_for(theme)
    ratio = contrast_ratio(palette.border, palette.bg)
    assert 1.05 <= ratio <= 4.0, f"{theme}: контраст рамки {ratio:.2f} вне диапазона"


def test_light_theme_is_warm_not_blue():
    """Светлая тема тёплая: красного больше синего, фон не белый и не синий."""
    palette = palette_for(THEME_LIGHT)
    r, g, b = parse_hex(palette.bg)
    assert r > b, "фон светлой темы должен быть тёплым (R > B)"
    assert b < 235, "фон не должен быть чисто-белым/голубоватым"
    assert palette.bg != "#FFFFFF"

    primary_r, primary_g, primary_b = parse_hex(palette.primary)
    assert primary_r > primary_b, "акцент светлой темы должен быть тёплым"


def test_dark_themes_are_dark():
    for theme in (THEME_DARK, THEME_HACKER, THEME_CUSTOM):
        palette = palette_for(theme)
        r, g, b = parse_hex(palette.bg)
        assert (r + g + b) / 3 < 60, f"{theme}: фон слишком светлый"


def test_hacker_theme_is_green_monochrome():
    palette = palette_for(THEME_HACKER)
    r, g, b = parse_hex(palette.primary)
    assert g > r and g > b, "акцент hacker-темы должен быть зелёным"
    assert "Mono" in palette.font_family or "monospace" in palette.font_family


# ── Пользовательская тема ─────────────────────────────────────────────────

def test_custom_theme_uses_user_colors():
    palette = custom_palette("#FF6B2C", "#101820")
    assert palette.primary == "#FF6B2C"
    assert palette.bg == "#101820"


def test_custom_theme_derives_readable_panels():
    """Панели и рамки выводятся из фона и остаются различимыми."""
    palette = custom_palette("#7C5CFF", "#14121D")
    assert palette.surface != palette.bg
    assert contrast_ratio(palette.surface, palette.bg) > 1.03
    assert contrast_ratio(palette.text, palette.bg) >= 4.5


@pytest.mark.parametrize(
    "accent",
    ["#FF6B2C", "#00E5FF", "#FFFFFF", "#000000", "#7C5CFF", "#39FF88"],
)
def test_custom_theme_text_on_any_accent(accent):
    """Текст на кнопке читается при любом цвете акцента."""
    palette = custom_palette(accent, "#101418")
    assert contrast_ratio(palette.primary_text, palette.primary) >= 4.4


def test_hex_parsing_accepts_short_forms():
    assert parse_hex("#FF6B2C") == (255, 107, 44)
    assert parse_hex("FF6B2C") == (255, 107, 44)
    assert parse_hex("  #ff6b2c  ") == (255, 107, 44)


@pytest.mark.parametrize("bad", ["", "#FFF", "#GGGGGG", "красный", None])
def test_invalid_color_gives_clear_error(bad):
    with pytest.raises(ValueError, match="RRGGBB"):
        parse_hex(bad)


def test_mix_interpolates():
    assert mix("#000000", "#FFFFFF", 0.0) == "#000000"
    assert mix("#000000", "#FFFFFF", 1.0) == "#FFFFFF"
    middle = parse_hex(mix("#000000", "#FFFFFF", 0.5))
    assert all(125 <= channel <= 130 for channel in middle)


def test_readable_text_color_picks_extreme():
    assert readable_text_color("#FFFFFF") == "#0B0F14"
    assert readable_text_color("#000000") == "#FFFFFF"


# ── CSS ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("theme", THEME_ORDER)
def test_css_contains_all_variables(theme):
    css = build_css(palette_for(theme))
    for token in REQUIRED_TOKENS:
        assert f"--rs-{token.replace('_', '-')}:" in css


@pytest.mark.parametrize("theme", THEME_ORDER)
def test_css_colors_external_components(theme):
    """Шапка, меню, карточки, поля, таблицы и уведомления — под контролем темы."""
    css = build_css(palette_for(theme))
    for selector in (
        "html, body",
        ".q-header",
        ".q-drawer",
        ".q-card",
        ".q-field__control",
        ".q-table",
        ".q-notification",
    ):
        assert selector in css, f"{theme}: нет стилей для {selector}"


def test_unknown_theme_is_rejected():
    with pytest.raises(ValueError, match="Неизвестная тема"):
        palette_for("rainbow")


def test_theme_info_covers_all_themes():
    assert set(THEME_INFO) == set(THEME_ORDER)
    for theme in THEME_ORDER:
        assert THEME_INFO[theme]["name"]
        assert THEME_INFO[theme]["description"]
        parse_hex(THEME_INFO[theme]["swatch"])  # цвет-образец корректен
