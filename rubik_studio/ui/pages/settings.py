from __future__ import annotations

from nicegui import ui

from rubik_studio.auth.middleware import current_user
from rubik_studio.auth.users import (
    AuthError,
    create_user,
    delete_user,
    list_users,
)
from rubik_studio.config import config
from rubik_studio.ui.layout import (
    confirm_dialog,
    create_page_layout,
    show_error,
    show_success,
    show_warning,
)


async def render() -> None:
    content = create_page_layout("Настройки")
    user = current_user() or {}

    with content:
        # ── Режим работы ────────────────────────────────────────────────

        with ui.card().classes("w-full"):
            ui.label("Режим работы").classes("text-lg font-semibold")

            current_mode = (
                "Desktop (локально)"
                if config.mode == "desktop"
                else "Server (по сети)"
            )

            ui.label(f"Текущий режим: {current_mode}")
            ui.label(f"База данных: {config.db_type}")

            ui.label(
                "Переключение режима потребует перезапуска приложения."
            ).classes("text-sm text-gray-500")

            if config.mode == "desktop":
                ui.button(
                    "Переключить в серверный режим",
                    icon="cloud",
                    on_click=lambda: confirm_switch("server"),
                )
            else:
                ui.button(
                    "Переключить в локальный режим",
                    icon="computer",
                    on_click=lambda: confirm_switch("desktop"),
                )

        # ── Пользователи ───────────────────────────────────────────────

        if user.get("role") == "admin":

            with ui.card().classes("w-full"):
                ui.label("Управление пользователями").classes(
                    "text-lg font-semibold"
                )

                users_container = ui.column().classes("w-full")

                async def refresh_users() -> None:
                    users_container.clear()

                    users = await list_users()

                    with users_container:
                        if not users:
                            ui.label("Пользователи отсутствуют.")
                            return

                        for account in users:
                            with ui.row().classes(
                                "w-full items-center justify-between"
                            ):
                                ui.label(
                                    f"{account.display_name} "
                                    f"({account.username}) — {account.role}"
                                )

                                if account.id != user.get("id"):
                                    ui.button(
                                        icon="delete",
                                        color="negative",
                                        on_click=lambda a=account: ask_delete_user(a),
                                    ).props("flat round")

                def open_create_user_dialog() -> None:
                    with ui.dialog() as dialog, ui.card().classes("w-96"):
                        ui.label("Новый пользователь").classes(
                            "text-lg font-bold"
                        )

                        username_input = ui.input("Логин").classes("w-full")
                        name_input = ui.input("Отображаемое имя").classes("w-full")
                        password_input = ui.input(
                            "Пароль",
                            password=True,
                        ).classes("w-full")

                        role_input = ui.select(
                            {
                                "admin": "Администратор",
                                "user": "Пользователь",
                                "viewer": "Наблюдатель",
                            },
                            value="user",
                            label="Роль",
                        ).classes("w-full")

                        async def save_user() -> None:
                            try:
                                await create_user(
                                    username=username_input.value,
                                    password=password_input.value,
                                    display_name=name_input.value,
                                    role=role_input.value,
                                    acting_username=user.get(
                                        "username", "local"
                                    ),
                                    acting_user_id=user.get("id"),
                                )

                            except AuthError as exc:
                                show_error(str(exc))
                                return

                            dialog.close()
                            show_success("Пользователь создан")
                            await refresh_users()

                        with ui.row().classes("w-full justify-end"):
                            ui.button(
                                "Отмена",
                                on_click=dialog.close,
                            ).props("flat")

                            ui.button(
                                "Создать",
                                on_click=save_user,
                                color="primary",
                            )

                    dialog.open()

                def ask_delete_user(account) -> None:
                    async def perform_delete() -> None:
                        try:
                            await delete_user(
                                user_id=account.id,
                                acting_user_id=user.get("id"),
                                acting_username=user.get(
                                    "username", "local"
                                ),
                            )

                        except AuthError as exc:
                            show_error(str(exc))
                            return

                        show_success("Пользователь удалён")
                        await refresh_users()

                    confirm_dialog(
                        "Удалить пользователя?",
                        (
                            f"Удалить пользователя "
                            f"«{account.username}»?\\n"
                            "Это действие нельзя отменить."
                        ),
                        perform_delete,
                    )

                ui.button(
                    "Добавить пользователя",
                    icon="person_add",
                    on_click=open_create_user_dialog,
                ).props("color=primary")

                await refresh_users()

        # ── Информация ─────────────────────────────────────────────────

        with ui.card().classes("w-full"):
            ui.label("О программе").classes("text-lg font-semibold")
            ui.label("RS — RUBIK STUDIO")
            ui.label("Версия 0.1.0")
            ui.label("Лицензия MIT")
            ui.label("Model. Mine. Automate.")


def confirm_switch(target_mode: str) -> None:
    """Запрос подтверждения изменения режима работы."""

    def perform_switch() -> None:
        if target_mode == "server":
            config.switch_to_server()
            show_warning(
                "Серверный режим включён. "
                "Перезапустите приложение. "
                "Обязательно смените стандартный пароль администратора!"
            )
        else:
            config.switch_to_desktop()
            show_success(
                "Локальный режим включён. "
                "Перезапустите приложение."
            )

    mode_name = (
        "серверный"
        if target_mode == "server"
        else "локальный"
    )

    confirm_dialog(
        "Переключить режим?",
        (
            f"Переключить приложение в {mode_name} режим?\\n\\n"
            "Изменения вступят в силу после перезапуска."
        ),
        perform_switch,
        confirm_label="Переключить",
    )
