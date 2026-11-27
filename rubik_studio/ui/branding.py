# RS_BRANDING_V57
"""Логотип RS: выбор файла под тему и вывод в интерфейсе.

Требование пользователя: **логотип обязателен**. Поэтому здесь нет
варианта «логотипа нет» — есть три уровня подстраховки:

1. штатный файл под текущую тему (``rubik_logo_light.png`` на светлой,
   ``rubik_logo_dark.png`` на тёмных);
2. если файла нет — исходный ``rubik_logo.png``;
3. если пропала вся папка assets — акцентный знак ``R``, нарисованный
   средствами темы, чтобы шапка не осталась пустой.

Для шапки (30 px) используется отдельный файл без надписи: подпись
«Rubik STUDIO» в таком размере не читается и превращается в серое пятно.
"""

from __future__ import annotations

import sys
from pathlib import Path

from nicegui import ui

from rubik_studio.core.themes_v56 import THEME_LIGHT


def _assets_root() -> Path:
    """Папка с ресурсами: работает и из исходников, и из EXE.

    В сжатой сборке PyInstaller (--onefile) файлы лежат во временной
    папке ``sys._MEIPASS``. Без этой проверки логотип в установленной
    программе не находился и подменялся буквой «R».
    """
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root) / "rubik_studio" / "assets"

    return Path(__file__).resolve().parent.parent / "assets"


ASSETS = _assets_root()

LOGO_LIGHT = ASSETS / "rubik_logo_light.png"
LOGO_DARK = ASSETS / "rubik_logo_dark.png"
LOGO_MARK = ASSETS / "rubik_logo_mark.png"
LOGO_SOURCE = ASSETS / "rubik_logo.png"

# Маршрут статики, смонтирован в main.py.
URL_PREFIX = "/rs-branding"


def _url(filename: str) -> str:
    return f"{URL_PREFIX}/{filename}"


def full_logo_url(theme_name: str) -> str:
    """Полный логотип (куб + надпись) для главной страницы и окна «О программе»."""
    if theme_name == THEME_LIGHT:
        return _url(LOGO_LIGHT.name) if LOGO_LIGHT.exists() else _url(LOGO_SOURCE.name)
    return _url(LOGO_DARK.name) if LOGO_DARK.exists() else _url(LOGO_SOURCE.name)


def header_logo_url(theme_name: str) -> str:
    """Знак без надписи для шапки: в 30 px работает только куб."""
    if LOGO_MARK.exists():
        return _url(LOGO_MARK.name)
    return full_logo_url(theme_name)


def has_logo_files() -> bool:
    """Есть ли хоть один файл логотипа на диске."""
    return any(path.exists() for path in (LOGO_LIGHT, LOGO_DARK, LOGO_MARK, LOGO_SOURCE))


def logo(size: int = 30, theme_name: str | None = None) -> None:
    """Показать логотип; при отсутствии файлов — знак из темы, но не пустота."""
    if theme_name is None:
        from rubik_studio.ui.theme import current_palette

        theme_name = current_palette().name

    if has_logo_files():
        ui.image(header_logo_url(theme_name)).style(
            f"width:{size}px; height:{size}px; object-fit:contain; flex:none;"
        )
        return

    # Крайний случай: файлов нет совсем. Знак рисуется цветом темы.
    ui.html(
        f'<div style="width:{size}px;height:{size}px;border-radius:6px;'
        f"background:var(--rs-primary);color:var(--rs-primary-text);"
        f"display:flex;align-items:center;justify-content:center;"
        f'font-weight:700;font-size:{round(size * 0.55)}px;">R</div>'
    ).style("flex:none;")
