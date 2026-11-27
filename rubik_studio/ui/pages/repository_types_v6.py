
from __future__ import annotations

from nicegui import ui

from rubik_studio.core.repository import (
    RepositoryError,
    repo_service,
)
from rubik_studio.ui.layout import (
    confirm_dialog,
    show_error,
    show_success,
)

# RS_CUSTOM_OBJECT_TYPES_V6
# RS_CUSTOM_TYPES_HINTS_V7


async def open_custom_types_dialog(
    database_id,
    database_name,
    user,
    on_changed,
):
    if not database_id:
        show_error("Выберите логическую базу")
        return

    with ui.dialog() as dialog, ui.card().classes(
        "w-full max-w-3xl"
    ):
        ui.label(
            "Пользовательские типы объектов"
        ).classes("text-xl font-bold")

        ui.label(
            f"Логическая база: {database_name}"
        ).classes("text-sm text-gray-500")

        ui.label(
            "Системные типы доступны во всех базах. "
            "Пользовательские типы принадлежат только этой базе."
        ).classes("text-sm")

        ui.label(
            "Тип помогает объединить похожие объекты. "
            "Например, можно создать тип «Договор» и затем "
            "добавлять объекты этого типа в репозиторий."
        ).classes("text-sm")

        ui.label(
            "Если подходящий системный тип уже существует, "
            "создавать новый необязательно. Пользовательский тип "
            "виден только в указанной выше базе."
        ).classes("text-sm")

        ui.label(
            "Тип нельзя удалить, пока он используется объектами. "
            "Пока эта функция управляет типами объектов; "
            "шаблоны целых процессов не реализованы."
        ).classes("text-sm")

        container = ui.column().classes("w-full gap-2")

        async def reload_types():
            try:
                types = await repo_service.list_types(database_id)
            except RepositoryError as exc:
                show_error(str(exc))
                return

            custom_types = [
                item for item in types
                if not item.is_system
                and item.database_id == database_id
            ]

            container.clear()

            with container:
                if not custom_types:
                    ui.label(
                        "Пользовательских типов пока нет."
                    ).classes("text-gray-500")

                for item in custom_types:
                    with ui.card().classes("w-full"):
                        with ui.row().classes(
                            "w-full items-center justify-between"
                        ):
                            with ui.column().classes("gap-0"):
                                ui.label(item.name).classes(
                                    "font-semibold"
                                )

                                ui.label(
                                    f"Цвет: {item.color or '#9E9E9E'}"
                                ).classes("text-sm text-gray-500")

                            with ui.row():
                                ui.button(
                                    icon="edit",
                                    on_click=lambda t=item:
                                        open_type_editor(t),
                                ).props("flat round").tooltip(
                                    "Изменить тип"
                                )

                                ui.button(
                                    icon="delete",
                                    color="negative",
                                    on_click=lambda t=item:
                                        ask_delete(t),
                                ).props("flat round").tooltip(
                                    "Удалить тип"
                                )

        def open_type_editor(existing=None):
            with ui.dialog() as editor, ui.card().classes(
                "w-full max-w-lg"
            ):
                ui.label(
                    "Изменение типа"
                    if existing is not None
                    else "Новый пользовательский тип"
                ).classes("text-lg font-bold")

                ui.label(
                    "Введите название, по которому пользователям "
                    "будет понятно назначение этого типа."
                ).classes("text-sm")

                name = ui.input(
                    "Название типа",
                    value=existing.name if existing else "",
                ).classes("w-full")

                color = ui.input(
                    "Цвет",
                    value=(
                        existing.color
                        if existing and existing.color
                        else "#9E9E9E"
                    ),
                ).classes("w-full")

                ui.label(
                    "Цвет задаётся в формате #RRGGBB, "
                    "например #1976D2."
                ).classes("text-xs text-gray-500")

                async def save():
                    try:
                        if existing is None:
                            await repo_service.create_custom_type(
                                database_id=database_id,
                                name=name.value,
                                color=color.value,
                                username=user.get(
                                    "username", "local"
                                ),
                                user_id=user.get("id"),
                            )
                        else:
                            await repo_service.update_custom_type(
                                database_id=database_id,
                                type_id=existing.id,
                                name=name.value,
                                color=color.value,
                                username=user.get(
                                    "username", "local"
                                ),
                                user_id=user.get("id"),
                            )

                    except (RepositoryError, ValueError) as exc:
                        show_error(str(exc))
                        return

                    editor.close()
                    show_success("Тип объекта сохранён")
                    await reload_types()
                    await on_changed()

                with ui.row().classes("w-full justify-end"):
                    ui.button(
                        "Отмена",
                        on_click=editor.close,
                    ).props("flat")

                    ui.button(
                        "Сохранить",
                        on_click=save,
                    )

            editor.open()

        async def ask_delete(item):
            try:
                count = (
                    await repo_service.count_custom_type_objects(
                        database_id,
                        item.id,
                    )
                )
            except RepositoryError as exc:
                show_error(str(exc))
                return

            if count:
                show_error(
                    f'Тип "{item.name}" используется объектами: '
                    f"{count}. Сначала удалите эти объекты."
                )
                return

            async def do_delete():
                try:
                    await repo_service.delete_custom_type(
                        database_id=database_id,
                        type_id=item.id,
                        username=user.get("username", "local"),
                        user_id=user.get("id"),
                    )
                except RepositoryError as exc:
                    show_error(str(exc))
                    return

                show_success("Тип объекта удалён")
                await reload_types()
                await on_changed()

            confirm_dialog(
                "Удаление типа",
                f'Удалить пользовательский тип "{item.name}"?',
                do_delete,
            )

        with ui.row().classes("w-full justify-between"):
            ui.button(
                "Добавить тип",
                icon="add",
                on_click=lambda: open_type_editor(),
            )

            ui.button(
                "Закрыть",
                on_click=dialog.close,
            ).props("flat")

    await reload_types()
    dialog.open()
