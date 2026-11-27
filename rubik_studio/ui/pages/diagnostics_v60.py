# RS_DIAGNOSTICS_V60
"""Страница диагностики: что работает, что под вопросом и что сломано.

Пользователь просил значок «!» — «ошибка/неисправность/нарушение:
показывает ошибку и почему она появилась» — и заметил, что он пригодится
для поиска багов. Здесь этот значок работает по назначению: страница
сама проверяет окружение и данные и показывает найденные проблемы с
причиной и местом.

Проверки намеренно «дешёвые» и без побочных эффектов: ничего не пишут в
базу, не меняют настройки, не требуют сети.
"""

from __future__ import annotations

import os
import platform
import sys
import tempfile
from pathlib import Path

from nicegui import ui

from rubik_studio.config import config
from rubik_studio.core import database
from rubik_studio.core.repository import repo_service
from rubik_studio.ui.hints_v60 import (
    KIND_ERROR,
    KIND_INFO,
    KIND_WARNING,
    hint_icon,
    info_badge,
    problem,
    render_problem,
    sort_problems,
)
from rubik_studio.ui.layout import create_page_layout


async def collect_checks() -> list[dict]:
    """Собрать результаты проверок.

    Возвращает список словарей ``problem()``: вид, заголовок, причина,
    место. Такой формат одинаково рисуется значком и попадает в отчёт.
    """
    items: list[dict] = []

    from rubik_studio import __version__

    items.append(
        problem(KIND_INFO, f"Версия приложения: {__version__}", "", "rubik_studio/__init__.py")
    )

    # 1. База данных: можно ли подключиться и есть ли обязательные таблицы.
    try:
        factory = database.get_session_factory()

        from sqlalchemy import func, select

        from rubik_studio.core.models import ModelType, ObjectType

        async with factory() as session:
            type_count = (
                await session.execute(select(func.count()).select_from(ObjectType))
            ).scalar_one()
            model_type_count = (
                await session.execute(select(func.count()).select_from(ModelType))
            ).scalar_one()

        if type_count == 0:
            items.append(
                problem(
                    KIND_ERROR,
                    "Справочник типов объектов пуст",
                    "Не выполнен начальный заполнение (seed) при создании базы",
                    "core/database.py, функция init_db",
                )
            )
        else:
            items.append(
                problem(
                    KIND_INFO,
                    f"База доступна, типов объектов: {type_count}",
                    "",
                    str(config.db_path or config.db_url or "sqlite"),
                )
            )

        if model_type_count == 0:
            items.append(
                problem(
                    KIND_WARNING,
                    "Нет типов моделей",
                    "Каталог моделей не заполнен, создание диаграмм идёт "
                    "через отдельный экспериментальный путь",
                    "таблица model_types",
                )
            )
    except Exception as exc:
        items.append(
            problem(
                KIND_ERROR,
                "Нет связи с базой данных",
                f"{type(exc).__name__}: {exc}",
                "core/database.py",
            )
        )

    # 2. Запись в папку данных: без неё не сохранятся настройки и база.
    try:
        data_dir = Path(config.data_dir) if config.data_dir else Path.cwd()
        data_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            dir=data_dir, prefix="rs-check-", delete=True
        ):
            pass

        items.append(
            problem(
                KIND_INFO,
                "Папка данных доступна для записи",
                "",
                str(data_dir),
            )
        )
    except Exception as exc:
        items.append(
            problem(
                KIND_ERROR,
                "Нет прав на запись в папку данных",
                f"{type(exc).__name__}: {exc}",
                "config.data_dir",
            )
        )

    # 3. Логотип: пользователь отдельно просил, чтобы он не исчезал.
    try:
        from rubik_studio.ui.branding import has_logo_files

        if has_logo_files():
            items.append(problem(KIND_INFO, "Логотип найден", "", "ui/branding.py"))
        else:
            items.append(
                problem(
                    KIND_WARNING,
                    "Файлы логотипа не найдены",
                    "Вместо изображения рисуется знак «R» цветом темы — "
                    "шапка не остаётся пустой",
                    "rubik_studio/assets",
                )
            )
    except Exception as exc:
        items.append(
            problem(
                KIND_ERROR,
                "Не удалось проверить логотип",
                f"{type(exc).__name__}: {exc}",
                "ui/branding.py",
            )
        )

    # 4. Сборка: из исходников или установленная программа.
    frozen = bool(getattr(sys, "frozen", False))
    items.append(
        problem(
            KIND_INFO,
            "Запуск из установленной программы" if frozen else "Запуск из исходников",
            "",
            sys.executable,
        )
    )

    # 5. Базы моделирования и объекты: быстрый обзор данных.
    try:
        bases = await repo_service.list_databases()
        objects_total = 0

        for base in bases:
            try:
                objects_total += len(
                    await repo_service.list_objects(database_id=base.id)
                )
            except Exception:
                items.append(
                    problem(
                        KIND_WARNING,
                        f"База «{base.name}» не читается",
                        "Список объектов не получен — возможно, база "
                        "повреждена или создана другой версией",
                        f"database_id={base.id}",
                    )
                )

        items.append(
            problem(
                KIND_INFO,
                f"Баз моделирования: {len(bases)}, объектов: {objects_total}",
                "",
                "репозиторий",
            )
        )
    except Exception as exc:
        items.append(
            problem(
                KIND_ERROR,
                "Не удалось прочитать список баз",
                f"{type(exc).__name__}: {exc}",
                "core/repository.py",
            )
        )

    # 6. Окружение: ОС и версия Python (минимум задан в pyproject.toml).
    items.append(
        problem(
            KIND_INFO,
            f"Python {platform.python_version()}, {platform.system()} "
            f"{platform.release()}",
            "",
            "окружение",
        )
    )

    if os.name != "nt":
        items.append(
            problem(
                KIND_WARNING,
                "Не Windows",
                "Установщик и автономная сборка рассчитаны на Windows 10/11; "
                "здесь проверяется только серверная часть",
                "build_installer.py",
            )
        )

    return items


def render_diagnostics_checks(items: list[dict]) -> None:
    """Показать проблемы, начиная с ошибок."""
    ordered = sort_problems(items)

    errors = [item for item in ordered if item["kind"] == KIND_ERROR]
    warnings = [item for item in ordered if item["kind"] == KIND_WARNING]

    with ui.row().classes("items-center gap-3"):
        ui.badge(f"Ошибок: {len(errors)}").props(
            "color=red" if errors else "color=grey"
        )
        ui.badge(f"Предупреждений: {len(warnings)}").props(
            "color=orange" if warnings else "color=grey"
        )
        ui.badge(f"Всего проверок: {len(ordered)}").props("color=grey")

    for item in ordered:
        with ui.card().classes("w-full"):
            render_problem(item)


async def render_diagnostics() -> None:
    """Страница «Диагностика»."""
    content = create_page_layout(
        "Диагностика",
        "Проверка окружения и данных: что в порядке, что под вопросом и что сломано.",
    )

    with content:
        ui.label(
            "Страница полезна, если что-то не открывается: она показывает "
            "причину и место, где искать."
        ).classes("text-sm")

        items = await collect_checks()
        render_diagnostics_checks(items)

        ui.separator()

        ui.label("Как читать значки").classes("text-base font-semibold")

        with ui.column().classes("gap-2"):
            with ui.row().classes("items-center gap-2 no-wrap"):
                hint_icon(
                    "Информация: так и должно быть. Значок ничего не требует.",
                    KIND_INFO,
                )
                ui.label("Информация — проверка пройдена").classes("text-sm")

            with ui.row().classes("items-center gap-2 no-wrap"):
                hint_icon(
                    "Возможная ошибка: работает, но может привести к "
                    "проблеме. Стоит обратить внимание.",
                    KIND_WARNING,
                )
                ui.label("Возможная ошибка — обратите внимание").classes("text-sm")

            with ui.row().classes("items-center gap-2 no-wrap"):
                hint_icon(
                    "Ошибка: что-то не работает. В подсказке — причина и "
                    "место, где искать.",
                    KIND_ERROR,
                )
                ui.label("Ошибка — не работает").classes("text-sm")

        info_badge(
            "Диагностика ничего не меняет: она только читает данные и "
            "проверяет права. Запускать её можно в любой момент.",
        )
