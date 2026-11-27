from __future__ import annotations

import inspect
from collections.abc import Callable

from nicegui import ui

from rubik_studio import __version__
from rubik_studio.auth.middleware import current_user, logout_user
from rubik_studio.config import config
from rubik_studio.ui.branding import logo
from rubik_studio.ui.theme import apply_theme

NAV_ITEMS = [
    ("Главная", "/", "home"),
    ("Репозиторий", "/repository", "inventory_2"),
    ("Базы данных", "/modeling-databases", "storage"),
    ("Моделирование", "/modeler", "account_tree"),
    ("Process Mining", "/mining", "insights"),
    ("Задачи и процессы", "/bpms", "task_alt"),
    ("Аудит-логи", "/logs", "history"),
    ("Настройки", "/settings", "settings"),
]


def show_error(message: str) -> None:
    ui.notify(message, type="negative", icon="error", position="top", timeout=6000, close_button="✕")


def show_warning(message: str) -> None:
    ui.notify(message, type="warning", icon="warning", position="top", timeout=5000, close_button="✕")


def show_success(message: str) -> None:
    ui.notify(message, type="positive", icon="check_circle", position="top", timeout=3000)


def confirm_dialog(
    title: str,
    message: str,
    on_confirm: Callable,
    confirm_label: str = "Удалить",
) -> None:
    with ui.dialog() as dialog, ui.card():
        ui.label(title).classes("text-lg font-bold")
        ui.label(message).classes("text-sm text-gray-600 whitespace-pre-line")
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Отмена", on_click=dialog.close).props("flat")

            async def _confirm() -> None:
                dialog.close()
                result = on_confirm()
                if inspect.isawaitable(result):
                    await result

            ui.button(confirm_label, on_click=_confirm, color="negative")
    dialog.open()


def empty_state(
    icon: str,
    message: str,
    action_label: str | None = None,
    on_action: Callable | None = None,
) -> None:
    with ui.column().classes("w-full items-center justify-center py-16 gap-3 text-gray-400"):
        ui.icon(icon).classes("text-6xl")
        ui.label(message).classes("text-base text-center max-w-md")
        if action_label and on_action:
            ui.button(action_label, on_click=on_action, icon="add").props("color=primary")


def create_header() -> None:
    """Шапка: цвета берутся из темы, логотип остаётся прежним."""
    user = current_user()
    with ui.header().classes("items-center justify-between px-4 rs-header"):
        with ui.row().classes("items-center gap-2"):
            logo(size=30)
            ui.label("RS — RUBIK STUDIO").classes("text-lg font-bold")
            ui.badge(f"v{__version__}").style(
                "background: var(--rs-surface-alt); color: var(--rs-text);"
            )
        with ui.row().classes("items-center gap-3"):
            mode_label = "🖥 Desktop" if config.mode == "desktop" else "🌐 Server"
            ui.label(mode_label).classes("text-sm rs-muted")
            if config.auth_enabled and user:
                ui.label(user.get("display_name", "")).classes("text-sm")
                ui.button(
                    icon="logout", on_click=lambda: (logout_user(), ui.navigate.to("/login"))
                ).props("flat round")


def create_sidebar() -> None:
    """Боковое меню в цветах темы; текущий раздел подсвечен акцентом."""
    from nicegui import context

    current_path = ""
    try:
        current_path = context.client.page.path
    except Exception:  # путь доступен не всегда (до сборки страницы)
        current_path = ""

    with ui.left_drawer(fixed=True).classes("p-2 rs-sidebar"):
        for label, path, icon in NAV_ITEMS:
            is_active = current_path == path
            button = ui.button(
                label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)
            ).props("flat no-caps align=left").classes("w-full justify-start mb-1")
            if is_active:
                button.style(
                    "color: var(--rs-primary); "
                    "background: var(--rs-surface-alt); "
                    "border-left: 3px solid var(--rs-primary);"
                )


def create_page_layout(title: str, subtitle: str = "") -> ui.column:
    """Общий каркас страницы: тема, шапка, меню и заголовок.

    Тема применяется здесь, поэтому каждая страница, построенная через
    этот макет, автоматически получает выбранное оформление.
    """
    apply_theme()
    create_header()
    create_sidebar()
    content = ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4 rs-app-shell")
    with content:
        ui.label(title).classes("text-2xl font-bold")
        if subtitle:
            ui.label(subtitle).classes("text-sm rs-muted")
    return content

# RS_NAVIGATION_ATTRIBUTES_V4
