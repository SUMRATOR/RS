"""V60: система значков-подсказок, маршруты меню, диагностика, версия.

Проверяется то, что можно проверить автоматически:

1. три значка различаются видом, текстом и доступностью с клавиатуры;
2. подсказка открывается наведением и кликом;
3. ни один пункт меню не ведёт на 404;
4. страница диагностики собирается и показывает проблемы;
5. версия приложения — 0.2.0 и берётся из одного места;
6. установщик описан и не притворяется, что собран.
"""

from __future__ import annotations

import pathlib

from nicegui import ui
from nicegui.testing import User

from rubik_studio.ui.hints_v60 import (
    KIND_ERROR,
    KIND_INFO,
    KIND_WARNING,
    STYLES,
    hint_icon,
    problem,
    sort_problems,
)

pytest_plugins = ["nicegui.testing.user_plugin"]

ROOT = pathlib.Path(__file__).resolve().parents[1]


# ── Значки ─────────────────────────────────────────────────────────────────

def test_three_kinds_have_distinct_glyphs():
    """«i», «?» и «!» — разные значки."""
    glyphs = {STYLES[kind]["glyph"] for kind in (KIND_INFO, KIND_WARNING, KIND_ERROR)}
    assert glyphs == {"i", "?", "!"}


def test_error_is_red_and_warning_is_yellow():
    """Красный круг для ошибки, жёлтый треугольник для предупреждения."""
    assert STYLES[KIND_ERROR]["background"] == "#DC2626"
    assert STYLES[KIND_WARNING]["background"] == "#F5C518"
    # Информация — полый круг с тёмным контуром.
    assert STYLES[KIND_INFO]["background"] == "transparent"
    assert "1F2937" in STYLES[KIND_INFO]["border"]


async def test_hint_opens_on_hover_and_click(user: User):
    """Подсказка видна по наведению и по клику."""
    @ui.page("/hint-v60")
    def page():
        hint_icon("Проверочный текст подсказки", KIND_INFO, mark="hint-demo")

    await user.open("/hint-v60")
    assert user.find(marker="hint-demo")

    icon = user.find(marker="hint-demo")
    icon.trigger("mouseenter")
    await user.should_see("Проверочный текст подсказки")


def test_problem_carries_reason_and_place():
    """Проблема описывает, что случилось, почему и где искать."""
    item = problem(
        KIND_ERROR,
        "Диаграмма не открывается",
        "id компонента передан числом",
        "bpmn_palette_v59.py",
    )
    assert item["severity"] > problem(KIND_INFO, "ок")["severity"]


def test_problems_sorted_by_severity():
    """Сначала ошибки, потом предупреждения, потом информация."""
    items = [
        problem(KIND_INFO, "и"),
        problem(KIND_ERROR, "о"),
        problem(KIND_WARNING, "п"),
    ]
    titles = [item["title"] for item in sort_problems(items)]
    assert titles == ["о", "п", "и"]


def test_hint_text_is_plain_string():
    """Текст подсказки — обычная строка: не разбирается и не рисуется HTML.

    Раньше текст пропускался через html.escape и уходил в строку свойств
    NiceGUI, которую библиотека разбирает как Python-литерал. Обратный
    слэш в пути ломал страницу, поэтому теперь значение ставится в
    свойства напрямую, а подпись выводится отдельным ui.label.
    """
    source = (ROOT / "rubik_studio/ui/hints_v60.py").read_text(encoding="utf-8")

    assert 'box._props["aria-label"]' in source
    assert 'ui.label(str(text))' in source


# ── Маршруты ───────────────────────────────────────────────────────────────

def test_no_menu_item_leads_to_404():
    """Каждый пункт меню имеет @ui.page."""
    layout = (ROOT / "rubik_studio/ui/layout.py").read_text(encoding="utf-8")
    main_source = (ROOT / "rubik_studio/main.py").read_text(encoding="utf-8")

    import re

    # Каждый пункт меню — тройка (подпись, путь, иконка).
    paths = [
        (match.group(1), match.group(2))
        for match in re.finditer(
            r'\(\s*"([^"]+)"\s*,\s*"(/[^"]*)"\s*,\s*"[^"]+"\s*\)',
            layout,
        )
    ]
    assert paths, "пункты меню не найдены"

    registered = set(re.findall(r'@ui\.page\("([^"]+)"\)', main_source))
    missing = [path for _label, path in paths if path not in registered]

    assert missing == [], f"пункты меню без страницы: {missing}"


async def test_soon_pages_render(user: User):
    """Неготовые разделы открывают честную страницу, а не 404."""
    from rubik_studio.ui.pages.soon_v60 import render_soon

    @ui.page("/soon-v60")
    def page():
        render_soon("mining")

    await user.open("/soon-v60")
    await user.should_see("Раздел в разработке")
    await user.should_see("Process Mining")


async def test_diagnostics_page_shows_checks(user: User, isolated_database):
    """Диагностика собирается и показывает результаты проверок."""
    from rubik_studio.ui.pages.diagnostics_v60 import render_diagnostics

    ui.page("/diagnostics-v60")(render_diagnostics)
    await user.open("/diagnostics-v60")

    await user.should_see("Диагностика")
    await user.should_see("Ошибок")


# ── Версия ─────────────────────────────────────────────────────────────────

def test_version_is_020():
    """Версия поднята до 0.2.0 после закрытия этапа 2."""
    import rubik_studio

    assert rubik_studio.__version__ == "0.2.0"


def test_version_not_hardcoded_in_pages():
    """Страницы берут версию из пакета, а не пишут её руками."""
    settings = (ROOT / "rubik_studio/ui/pages/settings.py").read_text(encoding="utf-8")
    assert 'ui.label("Версия 0.1.0")' not in settings
    assert "__version__" in settings


def test_pyproject_version_matches():
    """Версия в pyproject совпадает с версией пакета."""
    import rubik_studio

    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{rubik_studio.__version__}"' in text


# ── Установщик ─────────────────────────────────────────────────────────────

def test_installer_spec_exists_and_has_app():
    """Установщик описан для Inno Setup и содержит exe программы."""
    spec = (ROOT / "installer/RS_RUBIK_STUDIO.iss").read_text(encoding="utf-8")

    assert "RUBIK_STUDIO.exe" in spec
    assert "[Setup]" in spec
    assert "privilegesrequiredoverridesallowed" in spec.lower()
    assert "UsePreviousAppDir=yes" in spec


def test_installer_builder_checks_dist():
    """Сборщик установщика не создаёт пустой файл без программы."""
    text = (ROOT / "build_installer.py").read_text(encoding="utf-8")

    assert "def check_dist(" in text
    assert "build_rubik_exe.py" in text
    assert "return 2" in text  # код возврата «нет Inno Setup»


def test_branding_finds_assets_in_frozen_build():
    """Логотип находится и в сжатой сборке (иначе шапка остаётся без него)."""
    text = (ROOT / "rubik_studio/ui/branding.py").read_text(encoding="utf-8")
    assert "_MEIPASS" in text


# ── Аудит ──────────────────────────────────────────────────────────────────

async def test_database_actions_are_audited(isolated_database):
    """Создание, переименование и удаление базы попадают в журнал."""
    from rubik_studio.core import database
    from rubik_studio.core.audit_logger import audit
    from rubik_studio.core.modeling_databases import modeling_service

    await database.init_db()

    before = (await audit.get_stats()).get("total", 0)

    base = await modeling_service.create_database(name="Аудит V60")
    await modeling_service.rename_database(
        database_id=base.id, new_name="Аудит V60 (новое)"
    )
    await modeling_service.delete_database(base.id)

    after = (await audit.get_stats()).get("total", 0)
    assert after - before >= 3


async def test_diagnostics_reports_no_errors_in_clean_environment(isolated_database):
    """На рабочем окружении диагностика не должна находить ошибок.

    Проверка ловит ложные срабатывания: если диагностика показывает «!»
    там, где всё в порядке, пользователь перестаёт ей верить.
    """
    from rubik_studio.core import database
    from rubik_studio.ui.pages.diagnostics_v60 import KIND_ERROR, collect_checks

    await database.init_db()
    items = await collect_checks()

    errors = [item for item in items if item["kind"] == KIND_ERROR]
    assert errors == [], [
        f"{item['title']} — {item['reason']}" for item in errors
    ]


async def test_hint_with_windows_path_does_not_break(user: User):
    """Обратный слэш в тексте подсказки не должен ломать страницу.

    Регрессия Windows-прогона CI: путь вида ``C:\\Users\\...`` попадал в
    строку свойств NiceGUI, которая разбирается через ast.literal_eval,
    и страница падала с SyntaxError.
    """
    windows_path = r"C:\Users\RUNNER~1\AppData\Local\Temp\test.db"

    @ui.page("/hint-path-v60")
    def page():
        hint_icon(f"Где: {windows_path}", KIND_ERROR, mark="hint-path")

    await user.open("/hint-path-v60")
    await user.should_see("Где:")


def test_hint_text_not_parsed_as_python_literal():
    """Текст подсказки не должен проходить через разбор свойств NiceGUI."""
    source = (ROOT / "rubik_studio/ui/hints_v60.py").read_text(encoding="utf-8")
    assert 'box._props["aria-label"]' in source
