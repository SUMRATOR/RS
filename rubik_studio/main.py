"""
RS — RUBIK STUDIO
Точка входа приложения.
"""

import argparse
import asyncio
import logging
import sys

# RS_BRANDING_STATIC_V1
from pathlib import Path as _rs_branding_Path

from nicegui import app, ui

from rubik_studio.config import config
from rubik_studio.core.database import init_db
from rubik_studio.ui.branding import full_logo_url
from rubik_studio.ui.theme import current_palette

_rs_branding_assets = (
    _rs_branding_Path(__file__).resolve().parent
    / 'assets'
)
if _rs_branding_assets.is_dir():
    app.add_static_files(
        '/rs-branding',
        str(_rs_branding_assets),
    )



logger = logging.getLogger(__name__)


def preflight_checks():
    """Проверка условий запуска."""

    # Проверка версии нужна при запуске из исходников: в pyproject
    # указано ">=3.11", но распакованный архив запускают и старым Python.
    if sys.version_info < (3, 11):  # noqa: UP036 — осознанная проверка при запуске
        raise RuntimeError("Требуется Python 3.11 или новее")

    logger.info("Предварительные проверки запуска завершены")


def register_pages():
    """Регистрация страниц интерфейса."""

    # Импорт не «для галочки»: модули страниц регистрируют @ui.page
    # побочным эффектом. Удалять как неиспользуемый нельзя.
    from rubik_studio.ui.pages import (  # импорт ради регистрации @ui.page
        dashboard,
        login,
        logs_viewer,
        repository,
        settings,
    )

    # Страницы приложения регистрируются декораторами
    # @ui.page внутри соответствующих модулей.
    # Импорт выполняется до запуска NiceGUI.

    logger.info("Модули интерфейса загружены")



@ui.page("/")
async def rubik_home_page():
    """Главная страница: та же шапка, меню и тема, что и в остальных разделах."""

    # RS_HOME_LAYOUT_V59
    # Раньше это была отдельная «временная» страница без макета: у неё не
    # было шапки, меню и темы оформления, поэтому приложение выглядело
    # набором несвязанных окон. Теперь главная собирается тем же
    # create_page_layout, что и остальные разделы.
    from rubik_studio.ui.pages.dashboard import render as render_dashboard

    await render_dashboard()


# ============================================================
# МАРШРУТЫ СУЩЕСТВУЮЩИХ СТРАНИЦ
# ============================================================

@ui.page("/login")
async def rubik_login_page():
    from rubik_studio.ui.pages.login import render
    result = render()
    if asyncio.iscoroutine(result):
        await result


@ui.page("/dashboard")
async def rubik_dashboard_page():
    from rubik_studio.ui.pages.dashboard import render
    await render()


@ui.page("/repository")
async def rubik_repository_page():
    from rubik_studio.ui.pages.repository import render
    await render()


@ui.page("/logs")
async def rubik_logs_page():
    from rubik_studio.ui.pages.logs_viewer import render
    await render()


@ui.page("/settings")
async def rubik_settings_page():
    from rubik_studio.ui.pages.settings import render
    await render()


@ui.page("/modeling-databases")
async def rubik_modeling_databases_page():
    from rubik_studio.ui.pages.modeling_databases import render
    await render()


async def startup():
    """Инициализация базы данных."""

    await init_db()
    logger.info("База данных инициализирована")


def main():

    parser = argparse.ArgumentParser(
        description="RS — RUBIK STUDIO"
    )

    parser.add_argument(
        "--server",
        action="store_true",
        help="Запуск в серверном режиме",
    )

    parser.add_argument(
        "--host",
        default=None,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    preflight_checks()
    register_pages()

    app.on_startup(startup)

    mode = "server" if args.server else config.mode

    host = args.host or (
        "0.0.0.0" if mode == "server" else "127.0.0.1"
    )

    port = args.port or config.port

    ui.run(
        host=host,
        port=port,
        native=(mode == "desktop"),
        storage_secret=config.secret_key,
        reload=False,
    )


if __name__ == "__main__":
    main()
