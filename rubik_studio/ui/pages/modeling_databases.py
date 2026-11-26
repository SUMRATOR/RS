from __future__ import annotations

from nicegui import ui

from rubik_studio.core.modeling_databases import (
    ModelingError,
    modeling_service,
)


async def render() -> None:

    ui.button(
        "На главную",
        icon="arrow_back",
        on_click=lambda: ui.navigate.to("/"),
    ).props("flat")

    ui.label("Базы моделирования").classes("text-3xl font-bold")
    ui.label(
        "Создавайте независимые базы и выбирайте методологию моделирования."
    ).classes("text-gray-500")

    with ui.tabs().classes("w-full") as tabs:
        databases_tab = ui.tab("Логические базы")
        catalog_tab = ui.tab("Каталог моделей")

    with ui.tab_panels(tabs, value=databases_tab).classes("w-full"):

        with ui.tab_panel(databases_tab):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Логические базы").classes("text-xl font-semibold")
                ui.button(
                    "Создать базу",
                    icon="add",
                    on_click=lambda: open_create_dialog(),
                )

            database_container = ui.column().classes("w-full gap-3")

            async def refresh_databases():
                databases = await modeling_service.list_databases()
                database_container.clear()

                with database_container:
                    if not databases:
                        ui.label(
                            "Логических баз пока нет. Создайте первую базу."
                        ).classes("text-gray-500")
                        return

                    for database in databases:
                        with ui.card().classes("w-full"):
                            with ui.row().classes(
                                "w-full items-center justify-between"
                            ):
                                with ui.column().classes("gap-1"):
                                    ui.label(database.name).classes(
                                        "text-lg font-semibold"
                                    )
                                    ui.label(
                                        "Методология: "
                                        + (
                                            database.methodology.name
                                            if database.methodology else "—"
                                        )
                                    ).classes("text-sm text-gray-500")
                                    if database.description:
                                        ui.label(database.description).classes(
                                            "text-sm"
                                        )

                                ui.button(
                                    "Переименовать",
                                    icon="edit",
                                    on_click=lambda d=database: open_rename_dialog(d),
                                ).props("flat")

                                ui.button(
                                    "Удалить",
                                    icon="delete",
                                    color="negative",
                                    on_click=lambda d=database: open_delete_dialog(d),
                                ).props("flat")

            def open_create_dialog():
                with ui.dialog() as dialog, ui.card().classes("w-96"):
                    ui.label("Новая логическая база").classes(
                        "text-xl font-semibold"
                    )
                    name = ui.input("Название базы").classes("w-full")
                    description = ui.textarea("Описание").classes("w-full")
                    methodology = ui.select(
                        {
                            "STANDARD": "STANDARD — стандартная",
                            "EXTENDED": "EXTENDED — расширенная",
                            "FULL": "FULL — полная",
                        },
                        value="STANDARD",
                        label="Методология",
                    ).classes("w-full")

                    with ui.row().classes("w-full justify-end"):
                        ui.button("Отмена", on_click=dialog.close).props("flat")

                        async def save():
                            try:
                                await modeling_service.create_database(
                                    name=name.value,
                                    description=description.value,
                                    methodology_code=methodology.value,
                                )
                            except ModelingError as exc:
                                ui.notify(str(exc), type="negative")
                                return

                            dialog.close()
                            ui.notify("Логическая база создана", type="positive")
                            await refresh_databases()

                        ui.button("Создать", on_click=save)

                dialog.open()

            def open_rename_dialog(database):
                with ui.dialog() as dialog, ui.card().classes("w-96"):
                    ui.label("Переименование базы").classes(
                        "text-xl font-semibold"
                    )
                    name = ui.input(
                        "Новое название",
                        value=database.name,
                    ).classes("w-full")

                    with ui.row().classes("w-full justify-end"):
                        ui.button("Отмена", on_click=dialog.close).props("flat")

                        async def save():
                            try:
                                await modeling_service.rename_database(
                                    database.id,
                                    name.value,
                                )
                            except ModelingError as exc:
                                ui.notify(str(exc), type="negative")
                                return

                            dialog.close()
                            ui.notify("База переименована", type="positive")
                            await refresh_databases()

                        ui.button("Сохранить", on_click=save)

                dialog.open()


            def open_delete_dialog(database):
                with ui.dialog() as dialog, ui.card().classes("w-96"):
                    ui.label("Удаление логической базы").classes("text-xl")
                    ui.label(f'Удалить базу "{database.name}"?')
                    ui.label(
                        "Удаление необратимо. Можно удалить только пустую базу."
                    ).classes("text-red-600")

                    async def delete():
                        try:
                            await modeling_service.delete_database(database.id)
                        except ModelingError as exc:
                            ui.notify(str(exc), type="negative")
                            return

                        dialog.close()
                        ui.notify("База удалена", type="positive")
                        await refresh_databases()

                    with ui.row().classes("w-full justify-end"):
                        ui.button("Отмена", on_click=dialog.close).props("flat")
                        ui.button("Удалить", on_click=delete, color="negative")

                dialog.open()

            await refresh_databases()

        with ui.tab_panel(catalog_tab):
            ui.label("Встроенный каталог типов моделей").classes(
                "text-xl font-semibold"
            )

            with ui.row().classes("w-full items-center gap-3"):
                search = ui.input(
                    "Поиск по названию, сокращению или назначению"
                ).classes("flex-1")

                category = ui.select(
                    {"": "Все категории"},
                    value="",
                    label="Категория",
                ).classes("w-64")

            catalog_container = ui.column().classes("w-full gap-2")

            async def refresh_catalog():
                items = await modeling_service.search_model_types(
                    search=search.value,
                    category_code=category.value or None,
                )
                catalog_container.clear()

                with catalog_container:
                    ui.label(f"Найдено типов моделей: {len(items)}").classes(
                        "text-sm text-gray-500"
                    )

                    for item in items:
                        with ui.card().classes("w-full"):
                            with ui.row().classes(
                                "w-full items-center justify-between"
                            ):
                                with ui.column().classes("gap-1"):
                                    ui.label(
                                        f"{item.name} ({item.code})"
                                    ).classes("font-semibold")
                                    ui.label(item.description).classes(
                                        "text-sm text-gray-500"
                                    )

                                ui.badge(
                                    "В разработке"
                                    if item.editor_status != "AVAILABLE"
                                    else "Доступно",
                                    color=(
                                        "orange"
                                        if item.editor_status != "AVAILABLE"
                                        else "green"
                                    ),
                                )

            categories = await modeling_service.list_model_categories()
            category.options = {
                "": "Все категории",
                **{c.code: c.name for c in categories},
            }
            category.update()

            search.on("keydown.enter", lambda: refresh_catalog())
            category.on_value_change(lambda _: refresh_catalog())
            ui.button("Найти", on_click=refresh_catalog, icon="search")

            await refresh_catalog()
