from __future__ import annotations

# RS_OBJECT_TEMPLATES_UI_V8
# RS_TEMPLATE_EDIT_UI_V9
from nicegui import ui

from rubik_studio.core.object_templates_v8 import (
    FIELD_TYPES,
    create_object_from_template,
    create_template,
    delete_template,
    list_templates,
    update_template,
)
from rubik_studio.core.repository import RepositoryError, repo_service
from rubik_studio.ui.layout import (
    confirm_dialog,
    show_error,
    show_success,
)


async def open_templates_dialog(user):
    system_types = await repo_service.list_types()

    type_options = {
        item.id: item.name
        for item in system_types
        if item.is_system and item.database_id is None
    }

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-3xl"):
        ui.label("Общие трафареты объектов").classes(
            "text-xl font-bold"
        )

        ui.label(
            "Трафарет содержит тип объекта и заготовку полей. "
            "Его можно использовать в любой логической базе."
        ).classes("text-sm")

        ui.label(
            "Созданные объекты независимы. Удаление трафарета "
            "не удаляет объекты, созданные по нему."
        ).classes("text-sm")

        container = ui.column().classes("w-full gap-2")

        async def reload_templates():
            try:
                templates = await list_templates()
            except Exception as exc:
                show_error(f"Не удалось загрузить трафареты: {exc}")
                return

            container.clear()

            with container:
                if not templates:
                    ui.label(
                        "Трафаретов пока нет. Нажмите «Новый трафарет»."
                    )

                for template in templates:
                    with ui.card().classes("w-full"):
                        with ui.row().classes(
                            "w-full items-center justify-between"
                        ):
                            with ui.column().classes("gap-1"):
                                ui.label(template.name).classes(
                                    "font-semibold"
                                )

                                type_name = (
                                    template.object_type.name
                                    if template.object_type
                                    else "Тип не найден"
                                )

                                ui.label(
                                    f"Тип: {type_name}. "
                                    f"Полей: {len(template.fields or [])}"
                                ).classes("text-sm")

                                if template.description:
                                    ui.label(
                                        template.description
                                    ).classes("text-sm")

                            with ui.row():
                                ui.button(
                                    icon="edit",
                                    on_click=lambda t=template:
                                        open_new_template(t),
                                ).props("flat round").tooltip(
                                    "Изменить трафарет"
                                )

                                ui.button(
                                    icon="delete",
                                    color="negative",
                                    on_click=lambda t=template: ask_delete(t),
                                ).props("flat round").tooltip(
                                    "Удалить трафарет"
                                )

        def ask_delete(template):
            async def do_delete():
                try:
                    await delete_template(
                        template.id,
                        username=user.get("username", "local"),
                        user_id=user.get("id"),
                    )
                except RepositoryError as exc:
                    show_error(str(exc))
                    return

                show_success("Трафарет удалён")
                await reload_templates()

            confirm_dialog(
                "Удаление трафарета",
                (
                    f'Удалить трафарет «{template.name}»? '
                    "Созданные по нему объекты сохранятся."
                ),
                do_delete,
            )

        def open_new_template(existing=None):
            if not type_options:
                show_error("Нет доступных системных типов")
                return

            # Копируем поля, чтобы отмена не меняла данные
            # загруженного трафарета.
            fields = [
                dict(field)
                for field in (existing.fields or [])
            ] if existing is not None else []

            with ui.dialog() as editor, ui.card().classes(
                "w-full max-w-3xl"
            ):
                ui.label(
                    "Изменение трафарета"
                    if existing is not None
                    else "Новый трафарет"
                ).classes("text-lg font-bold")

                ui.label(
                    "Изменения трафарета применяются только при "
                    "создании новых объектов. Уже созданные объекты "
                    "не изменяются."
                ).classes("text-sm")

                ui.label(
                    "Выберите системный тип и добавьте поля, "
                    "которые должны появляться при создании объекта."
                ).classes("text-sm")

                name_input = ui.input(
                    "Название трафарета",
                    value=existing.name if existing is not None else "",
                ).classes("w-full")

                description_input = ui.textarea(
                    "Описание трафарета",
                    value=(
                        existing.description or ""
                        if existing is not None
                        else ""
                    ),
                ).classes("w-full")

                type_select = ui.select(
                    type_options,
                    value=(
                        existing.type_id
                        if existing is not None
                        else None
                    ),
                    label="Системный тип объекта",
                ).classes("w-full")

                ui.label(
                    "Поля трафарета"
                ).classes("font-semibold")

                fields_container = ui.column().classes(
                    "w-full gap-2"
                )

                def refresh_fields():
                    fields_container.clear()

                    with fields_container:
                        if not fields:
                            ui.label(
                                "Полей пока нет. Их можно добавить ниже."
                            ).classes("text-sm")

                        for index, field in enumerate(fields):
                            with ui.row().classes(
                                "w-full items-center justify-between"
                            ):
                                default = field["default"]

                                if field["kind"] == "boolean":
                                    default = "Да" if default else "Нет"

                                ui.label(
                                    f'{field["name"]} — '
                                    f'{FIELD_TYPES[field["kind"]]}, '
                                    f'по умолчанию: {default or "—"}'
                                ).classes("flex-1")

                                ui.button(
                                    icon="edit",
                                    on_click=lambda i=index: open_add_field(i),
                                ).props("flat round").tooltip(
                                    "Изменить поле"
                                )

                                ui.button(
                                    icon="delete",
                                    color="negative",
                                    on_click=lambda i=index: remove_field(i),
                                ).props("flat round").tooltip(
                                    "Удалить поле"
                                )

                def remove_field(index):
                    fields.pop(index)
                    refresh_fields()

                def open_add_field(edit_index=None):
                    original = (
                        dict(fields[edit_index])
                        if edit_index is not None
                        else None
                    )

                    with ui.dialog() as field_dialog, ui.card().classes(
                        "w-full max-w-lg"
                    ):
                        ui.label(
                            "Изменение поля"
                            if original is not None
                            else "Новое поле"
                        ).classes("text-lg font-semibold")

                        field_name = ui.input(
                            "Название поля",
                            value=original["name"] if original else "",
                        ).classes("w-full")

                        field_kind = ui.select(
                            FIELD_TYPES,
                            value=original["kind"] if original else "string",
                            label="Тип значения",
                        ).classes("w-full")

                        default_container = ui.column().classes("w-full")
                        state = {"input": None}

                        def render_default():
                            default_container.clear()

                            with default_container:
                                if field_kind.value == "boolean":
                                    state["input"] = ui.checkbox(
                                        "По умолчанию: Да",
                                        value=(
                                            bool(original["default"])
                                            if original is not None
                                            and original["kind"] == "boolean"
                                            else False
                                        ),
                                    )
                                else:
                                    initial = (
                                        str(original["default"] or "")
                                        if original is not None
                                        and original["kind"] == field_kind.value
                                        else ""
                                    )

                                    state["input"] = ui.input(
                                        "Значение по умолчанию",
                                        value=initial,
                                    ).classes("w-full")

                                    if field_kind.value == "date":
                                        ui.label(
                                            "Формат даты: ГГГГ-ММ-ДД"
                                        ).classes("text-sm")

                                    if field_kind.value == "number":
                                        ui.label(
                                            "Например: 1500 или 12,5"
                                        ).classes("text-sm")

                        field_kind.on_value_change(
                            lambda _: render_default()
                        )

                        render_default()

                        def add_field():
                            name = (field_name.value or "").strip()

                            if not name:
                                show_error("Введите название поля")
                                return

                            if any(
                                item["name"].casefold() == name.casefold()
                                for index, item in enumerate(fields)
                                if index != edit_index
                            ):
                                show_error(
                                    "Поле с таким названием уже добавлено"
                                )
                                return

                            if edit_index is None and len(fields) >= 50:
                                show_error(
                                    "Допускается не более 50 полей"
                                )
                                return

                            new_field = {
                                "name": name,
                                "kind": field_kind.value,
                                "default": state["input"].value,
                            }

                            if edit_index is None:
                                fields.append(new_field)
                            else:
                                fields[edit_index] = new_field

                            field_dialog.close()
                            refresh_fields()

                        with ui.row().classes("w-full justify-end"):
                            ui.button(
                                "Отмена",
                                on_click=field_dialog.close,
                            ).props("flat")

                            ui.button(
                                (
                                    "Сохранить поле"
                                    if original is not None
                                    else "Добавить поле"
                                ),
                                on_click=add_field,
                            )

                    field_dialog.open()

                ui.button(
                    "Добавить поле",
                    icon="add",
                    on_click=open_add_field,
                ).props("outline")

                refresh_fields()

                async def save():
                    try:
                        if existing is None:
                            await create_template(
                                name=name_input.value,
                                description=description_input.value,
                                type_id=type_select.value,
                                fields=fields,
                                username=user.get("username", "local"),
                                user_id=user.get("id"),
                            )
                        else:
                            await update_template(
                                template_id=existing.id,
                                name=name_input.value,
                                description=description_input.value,
                                type_id=type_select.value,
                                fields=fields,
                                username=user.get("username", "local"),
                                user_id=user.get("id"),
                            )
                    except (RepositoryError, ValueError) as exc:
                        show_error(str(exc))
                        return

                    editor.close()
                    show_success(
                        "Трафарет сохранён"
                        if existing is not None
                        else "Трафарет создан"
                    )
                    await reload_templates()

                with ui.row().classes("w-full justify-end"):
                    ui.button(
                        "Отмена",
                        on_click=editor.close,
                    ).props("flat")

                    ui.button(
                        (
                            "Сохранить изменения"
                            if existing is not None
                            else "Создать трафарет"
                        ),
                        on_click=save,
                    )

            editor.open()

        with ui.row().classes("w-full justify-between"):
            ui.button(
                "Новый трафарет",
                icon="add",
                on_click=open_new_template,
            )

            ui.button(
                "Закрыть",
                on_click=dialog.close,
            ).props("flat")

    await reload_templates()
    dialog.open()


async def open_create_from_template_dialog(
    database_id,
    database_name,
    user,
    on_created,
):
    if not database_id:
        show_error("Выберите логическую базу")
        return

    try:
        templates = await list_templates()
    except Exception as exc:
        show_error(f"Не удалось загрузить трафареты: {exc}")
        return

    if not templates:
        show_error(
            "Сначала создайте трафарет кнопкой «Трафареты объектов»"
        )
        return

    template_by_id = {item.id: item for item in templates}
    options = {item.id: item.name for item in templates}

    with ui.dialog() as dialog, ui.card().classes(
        "w-full max-w-3xl"
    ):
        ui.label("Создать объект по трафарету").classes(
            "text-xl font-bold"
        )

        ui.label(
            f"Объект будет создан в базе: {database_name}"
        ).classes("text-sm")

        ui.label(
            "Выберите трафарет, введите название объекта "
            "и при необходимости измените готовые значения."
        ).classes("text-sm")

        template_select = ui.select(
            options,
            label="Трафарет",
        ).classes("w-full")

        name_input = ui.input(
            "Название нового объекта"
        ).classes("w-full")

        description_input = ui.textarea(
            "Описание нового объекта"
        ).classes("w-full")

        type_label = ui.label("").classes("text-sm")
        values_container = ui.column().classes("w-full gap-2")
        value_inputs = {}

        def render_fields():
            values_container.clear()
            value_inputs.clear()

            template = template_by_id.get(template_select.value)

            if template is None:
                type_label.text = ""
                type_label.update()
                return

            type_name = (
                template.object_type.name
                if template.object_type
                else "Тип не найден"
            )

            type_label.text = f"Тип объекта: {type_name}"
            type_label.update()

            with values_container:
                if not template.fields:
                    ui.label(
                        "В этом трафарете нет дополнительных полей."
                    ).classes("text-sm")

                for field in template.fields or []:
                    name = field.get("name", "")
                    kind = field.get("kind", "string")
                    default = field.get("default", "")

                    if kind == "boolean":
                        value_inputs[name] = ui.checkbox(
                            name,
                            value=bool(default),
                        )
                    else:
                        value_inputs[name] = ui.input(
                            name,
                            value=str(default or ""),
                        ).classes("w-full")

                        if kind == "date":
                            ui.label(
                                "Формат даты: ГГГГ-ММ-ДД"
                            ).classes("text-sm")

                        elif kind == "number":
                            ui.label(
                                "Введите число или оставьте поле пустым."
                            ).classes("text-sm")

        template_select.on_value_change(
            lambda _: render_fields()
        )

        async def save():
            template_id = template_select.value

            if not template_id:
                show_error("Выберите трафарет")
                return

            values = {
                name: component.value
                for name, component in value_inputs.items()
            }

            try:
                await create_object_from_template(
                    database_id=database_id,
                    template_id=template_id,
                    name=name_input.value,
                    description=description_input.value,
                    values=values,
                    username=user.get("username", "local"),
                    user_id=user.get("id"),
                )
            except (RepositoryError, ValueError) as exc:
                show_error(str(exc))
                return

            dialog.close()
            show_success("Объект создан по трафарету")
            await on_created()

        with ui.row().classes("w-full justify-end"):
            ui.button(
                "Отмена",
                on_click=dialog.close,
            ).props("flat")

            ui.button(
                "Создать объект",
                on_click=save,
            )

    dialog.open()
