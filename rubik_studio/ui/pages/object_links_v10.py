from __future__ import annotations

# RS_OBJECT_LINKS_UI_V10
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

LINK_TYPES = {
    "USES": "Использует",
    "RESPONSIBLE_FOR": "Отвечает за",
    "GENERATES": "Создаёт",
    "MITIGATES": "Снижает",
    "SUPPORTS": "Поддерживает",
}


def object_caption(obj):
    """Подпись помогает различать объекты с одинаковыми названиями."""

    type_name = obj.type.name if obj.type else "Неизвестный тип"

    return f"{obj.name} — {type_name} [{str(obj.id)[:8]}]"


async def open_object_links_dialog(
    database_id,
    database_name,
    user,
):
    """Открывает связи фиксированной логической базы."""

    if not database_id:
        show_error("Выберите логическую базу")
        return

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-4xl"):
        ui.label("Связи объектов").classes("text-xl font-bold")

        ui.label(
            f"Логическая база: {database_name}"
        ).classes("text-sm")

        ui.label(
            "Связь показывает отношение одного объекта к другому. "
            "Например: процесс «Закупка» использует документ «Заявка»."
        ).classes("text-sm")

        ui.label(
            "Направление важно: сначала выбирается исходный объект, "
            "затем отношение и связанный объект. Связывать объекты "
            "разных баз нельзя."
        ).classes("text-sm")

        objects_container = ui.column().classes("w-full gap-2")

        async def reload_links():
            try:
                objects = await repo_service.list_objects(
                    database_id=database_id,
                )

                links = await repo_service.list_links(
                    database_id=database_id,
                )

            except RepositoryError as exc:
                show_error(str(exc))
                return

            object_names = {
                obj.id: object_caption(obj)
                for obj in objects
            }

            objects_container.clear()

            with objects_container:
                if not links:
                    ui.label(
                        "В этой базе пока нет связей."
                    ).classes("text-sm")

                for link in links:
                    source_name = object_names.get(
                        link.source_id,
                        f"Объект не найден: {link.source_id}",
                    )

                    target_name = object_names.get(
                        link.target_id,
                        f"Объект не найден: {link.target_id}",
                    )

                    relation_name = LINK_TYPES.get(
                        link.link_type,
                        link.link_type,
                    )

                    with ui.card().classes("w-full"):
                        with ui.row().classes(
                            "w-full items-center justify-between"
                        ):
                            with ui.column().classes("gap-1 flex-1"):
                                ui.label(
                                    f"От: {source_name}"
                                ).classes("font-semibold")

                                ui.label(
                                    f"Отношение: {relation_name}"
                                ).classes("text-sm")

                                ui.label(
                                    f"К: {target_name}"
                                ).classes("text-sm")

                            ui.button(
                                icon="delete",
                                color="negative",
                                on_click=lambda item=link: ask_delete(item),
                            ).props("flat round").tooltip(
                                "Удалить связь"
                            )

        def ask_delete(link):
            async def delete_selected():
                try:
                    await repo_service.delete_link(
                        database_id=database_id,
                        link_id=link.id,
                        username=user.get("username", "local"),
                        user_id=user.get("id"),
                    )
                except RepositoryError as exc:
                    show_error(str(exc))
                    return

                show_success("Связь удалена")
                await reload_links()

            confirm_dialog(
                "Удаление связи",
                (
                    "Удалить эту связь? "
                    "Сами объекты удалены не будут."
                ),
                delete_selected,
            )

        async def open_create_dialog():
            try:
                objects = await repo_service.list_objects(
                    database_id=database_id,
                )
            except RepositoryError as exc:
                show_error(str(exc))
                return

            if len(objects) < 2:
                show_error(
                    "Для создания связи нужны как минимум "
                    "два объекта в этой базе."
                )
                return

            options = {
                obj.id: object_caption(obj)
                for obj in objects
            }

            with ui.dialog() as create_dialog, ui.card().classes(
                "w-full max-w-2xl"
            ):
                ui.label("Новая связь").classes(
                    "text-lg font-bold"
                )

                ui.label(
                    "Выберите исходный объект, отношение и объект, "
                    "к которому оно направлено."
                ).classes("text-sm")

                source_select = ui.select(
                    options,
                    label="Исходный объект — от кого или от чего",
                ).classes("w-full")

                relation_select = ui.select(
                    LINK_TYPES,
                    label="Отношение",
                ).classes("w-full")

                target_select = ui.select(
                    options,
                    label="Связанный объект — к кому или к чему",
                ).classes("w-full")

                ui.label(
                    "Например: процесс «Закупка» → использует → "
                    "документ «Заявка»."
                ).classes("text-sm")

                async def save_link():
                    source_id = source_select.value
                    target_id = target_select.value
                    link_type = relation_select.value

                    if not source_id:
                        show_error("Выберите исходный объект")
                        return

                    if not link_type:
                        show_error("Выберите отношение")
                        return

                    if link_type not in LINK_TYPES:
                        show_error("Выберите допустимое отношение")
                        return

                    if not target_id:
                        show_error("Выберите связанный объект")
                        return

                    if source_id == target_id:
                        show_error(
                            "Нельзя связать объект с самим собой"
                        )
                        return

                    try:
                        await repo_service.create_link(
                            database_id=database_id,
                            source_id=source_id,
                            target_id=target_id,
                            link_type=link_type,
                            username=user.get("username", "local"),
                            user_id=user.get("id"),
                        )
                    except (RepositoryError, ValueError) as exc:
                        show_error(str(exc))
                        return

                    create_dialog.close()
                    show_success("Связь создана")
                    await reload_links()

                with ui.row().classes("w-full justify-end"):
                    ui.button(
                        "Отмена",
                        on_click=create_dialog.close,
                    ).props("flat")

                    ui.button(
                        "Создать связь",
                        on_click=save_link,
                    )

            create_dialog.open()

        with ui.row().classes("w-full justify-between"):
            ui.button(
                "Создать связь",
                icon="add_link",
                on_click=open_create_dialog,
            )

            ui.button(
                "Закрыть",
                on_click=dialog.close,
            ).props("flat")

    await reload_links()
    dialog.open()
