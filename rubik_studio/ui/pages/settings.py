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
from rubik_studio.core.themes_v56 import (
    THEME_CUSTOM,
    THEME_INFO,
    THEME_ORDER,
    contrast_ratio,
    palette_for,
    parse_hex,
    to_hex,
)
from rubik_studio.ui.branding import logo
from rubik_studio.ui.layout import (
    confirm_dialog,
    create_page_layout,
    show_error,
    show_success,
    show_warning,
)
from rubik_studio.ui.theme import apply_theme_live


async def render() -> None:
    content = create_page_layout("Настройки")
    user = current_user() or {}

    with content:
        # ── Оформление (RS_THEMES_V56) ──────────────────────────────────

        render_theme_settings()

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
            logo(size=64)
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


# RS_THEMES_V56
def render_theme_settings() -> None:
    """Блок «Оформление»: выбор темы и цветов «своей тёмной».

    Все изменения сохраняются в config.json и применяются сразу:
    страница перерисовывается без перезапуска приложения.
    """
    with ui.card().classes("w-full"):
        ui.label("Оформление").classes("text-lg font-semibold")
        ui.label(
            "Тема применяется сразу ко всему интерфейсу: меню, таблицы, "
            "карточки и поле диаграммы."
        ).classes("text-sm text-gray-500")

        # Понятные названия вместо кодов в конфиге.
        options = {key: THEME_INFO[key]["name"] for key in THEME_ORDER}

        def describe(theme_key: str) -> str:
            return THEME_INFO.get(theme_key, {}).get("description", "")

        with ui.row().classes("w-full items-start gap-4 mt-2 no-wrap"):
            theme_select = ui.select(
                options,
                value=config.theme if config.theme in options else "dark",
                label="Тема",
                on_change=lambda e: _save_theme(e.value),
            ).classes("w-64")

            with ui.column().classes("gap-1"):
                description = ui.label(
                    describe(theme_select.value)
                ).classes("text-sm text-gray-500")
                swatch = ui.html(_swatch_html(theme_select.value))

        # ── Своя тёмная: акцент и фон ───────────────────────────────────

        custom_box = ui.column().classes("w-full gap-2 mt-2")

        with custom_box:
            ui.label(
                "Своя тёмная тема: выберите цвет подсветки и фон. "
                "Фон всегда остаётся тёмным — слишком светлый будет "
                "затемнён автоматически, чтобы текст оставался читаемым."
            ).classes("text-sm text-gray-500")

            with ui.row().classes("items-center gap-4"):
                accent_input = ui.color_input(
                    "Цвет подсветки",
                    value=config.theme_accent,
                ).classes("w-56")

                background_input = ui.color_input(
                    "Фон",
                    value=config.theme_background,
                ).classes("w-56")

            preview_box = ui.column().classes("gap-1")
            warning = ui.label("").classes("text-sm text-orange-600")

            def update_preview():
                try:
                    palette = palette_for(
                        THEME_CUSTOM,
                        accent_input.value,
                        background_input.value,
                    )
                except ValueError as exc:
                    warning.set_text(str(exc))
                    preview_box.clear()
                    return

                warning.set_text("")

                ratio = contrast_ratio(palette.text, palette.bg)
                note = ""
                try:
                    # Сравниваем цвета в одном виде: пользователь мог ввести
                    # фон без «#» или строчными буквами.
                    asked_bg = to_hex(parse_hex(background_input.value))
                except (ValueError, TypeError):
                    asked_bg = ""
                if asked_bg and palette.bg.upper() != asked_bg.upper():
                    note = " (фон затемнён для читаемости)"

                preview_box.clear()
                with preview_box:
                    ui.html(
                        f'<div style="background:{palette.bg};'
                        f'border:1px solid {palette.border};border-radius:10px;'
                        f'padding:12px;width:320px;">'
                        f'<div style="color:{palette.text};font-weight:600;'
                        f'font-size:14px;">Так выглядит текст</div>'
                        f'<div style="color:{palette.text_muted};font-size:12px;'
                        f'margin-top:4px;">Подпись и пояснение</div>'
                        f'<div style="margin-top:10px;background:{palette.primary};'
                        f'color:{palette.primary_text};padding:6px 14px;'
                        f'border-radius:8px;display:inline-block;'
                        f'font-size:13px;font-weight:600;">Кнопка</div>'
                        f'</div>'
                    )
                    ui.label(
                        f"Контраст текста: {ratio:.1f}:1{note}"
                    ).classes("text-xs text-gray-500")

            def save_custom(e=None):
                config.theme = THEME_CUSTOM
                config.theme_accent = str(accent_input.value)
                config.theme_background = str(background_input.value)
                config.save()
                update_preview()
                apply_theme_live()
                show_success("Своя тёмная тема применена.")

            accent_input.on_value_change(lambda _e: update_preview())
            background_input.on_value_change(lambda _e: update_preview())

            with ui.row().classes("gap-2"):
                ui.button(
                    "Применить свою тему",
                    icon="palette",
                    on_click=save_custom,
                ).props("color=primary")

                ui.button(
                    "Сбросить к тёмной",
                    icon="restart_alt",
                    on_click=lambda: _reset_to_dark(theme_select),
                ).props("flat")

            update_preview()

        def _save_theme(theme_key: str):
            config.theme = theme_key
            config.save()
            description.set_text(describe(theme_key))
            swatch.set_content(_swatch_html(theme_key))

            # Перекрашиваем открытую страницу сразу: перезагрузка не нужна,
            # введённые данные на странице не теряются.
            apply_theme_live()

            show_success(
                f"Выбрана тема «{options.get(theme_key, theme_key)}». "
                "Она уже применена к этому разделу и применится к "
                "остальным при их открытии."
            )

        def _reset_to_dark(select):
            config.theme = "dark"
            config.save()
            select.value = "dark"
            select.update()
            description.set_text(describe("dark"))
            swatch.set_content(_swatch_html("dark"))
            apply_theme_live()
            show_success("Возвращена тёмная тема.")


def _swatch_html(theme_key: str) -> str:
    """Полоска-образец: фон, панель и подсветка выбранной темы."""
    try:
        palette = palette_for(theme_key, config.theme_accent, config.theme_background)
    except ValueError:
        palette = palette_for("dark")
    return (
        f'<div style="display:flex;align-items:center;gap:6px;">'
        f'<div style="width:26px;height:26px;border-radius:6px;'
        f'background:{palette.bg};border:1px solid {palette.border};"></div>'
        f'<div style="width:26px;height:26px;border-radius:6px;'
        f'background:{palette.surface};border:1px solid {palette.border};"></div>'
        f'<div style="width:26px;height:26px;border-radius:6px;'
        f'background:{palette.primary};"></div>'
        f'</div>'
    )
