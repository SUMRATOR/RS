
from __future__ import annotations
# RS_BPMN_REPOSITORY_FLOWS_V43

from datetime import date
from decimal import Decimal, InvalidOperation

from nicegui import ui

from rubik_studio.auth.middleware import current_user
from rubik_studio.core.repository import RepositoryError, repo_service
from rubik_studio.ui.pages.object_links_v10 import (
    open_object_links_dialog,
)
from rubik_studio.ui.pages.object_templates_v8 import (
    open_create_from_template_dialog,
    open_templates_dialog,
)

from rubik_studio.ui.layout import (
    confirm_dialog,
    create_page_layout,
    show_error,
    show_success,
)

# RS_NAVIGATION_ATTRIBUTES_V4
# RS_REPOSITORY_HINTS_V7


ATTRIBUTE_TYPES = {
    "string": "Строка",
    "number": "Число",
    "date": "Дата",
    "boolean": "Логическое значение",
}


def decode_attribute(value):
    if isinstance(value, bool):
        return "boolean", value

    if isinstance(value, (int, float)):
        return "number", str(value)

    if isinstance(value, str):
        return "string", value

    if isinstance(value, dict) and value.get("__rs_type__") == "date":
        return "date", value.get("value", "")

    return "string", str(value)


def encode_attribute(kind, value):
    if kind == "string":
        return str(value or "")

    if kind == "number":
        text = str(value or "").strip().replace(",", ".")

        if not text:
            raise ValueError("Введите числовое значение")

        try:
            number = Decimal(text)
        except InvalidOperation:
            raise ValueError("Некорректное число")

        if not number.is_finite():
            raise ValueError("Число должно быть конечным")

        if number == number.to_integral_value():
            return int(number)

        return float(number)

    if kind == "date":
        text = str(value or "").strip()

        try:
            date.fromisoformat(text)
        except ValueError:
            raise ValueError("Дата должна иметь формат ГГГГ-ММ-ДД")

        return {
            "__rs_type__": "date",
            "value": text,
        }

    if kind == "boolean":
        return bool(value)

    raise ValueError("Неизвестный тип атрибута")


def attribute_text(value):
    kind, decoded = decode_attribute(value)

    if kind == "boolean":
        return "Да" if decoded else "Нет"

    if kind == "date":
        return str(decoded)

    return str(decoded)


async def render():
    content = create_page_layout("Репозиторий объектов")
    user = current_user() or {}

    databases = await repo_service.list_databases()
    database_options = {item.id: item.name for item in databases}

    with content:
        ui.label("Независимые репозитории объектов").classes(
            "text-xl font-bold"
        )

        ui.label(
            "Здесь хранятся объекты выбранной логической базы: "
            "например, процессы, документы, роли и подразделения. "
            "Объекты разных баз независимы."
        ).classes("text-sm")

        ui.label(
            "Как начать: выберите базу, создайте объект, затем откройте "
            "его карточку и заполните описание и атрибуты."
        ).classes("text-sm")

        ui.label(
            "В будущем готовые объекты можно будет добавлять "
            "на диаграммы этой же базы. Графические редакторы "
            "пока находятся в разработке."
        ).classes("text-sm")

        if not databases:
            ui.label(
                "Сначала создайте логическую базу моделирования."
            ).classes("text-orange-600")

            ui.button(
                "Перейти к базам данных",
                on_click=lambda: ui.navigate.to("/modeling-databases"),
            )
            return

        database_select = ui.select(
            database_options,
            value=databases[0].id,
            label="Логическая база",
        ).classes("w-full")

        ui.label(
            "Выберите базу: ниже будут показаны только её объекты. "
            "Переход к другой базе не переносит объекты."
        ).classes("text-sm")

        search_input = ui.input(
            "Поиск по названию"
        ).classes("w-full")

        ui.label(
            "Для поиска введите название и нажмите Enter "
            "или кнопку «Найти». Тип можно использовать как фильтр."
        ).classes("text-sm")

        type_select = ui.select(
            {None: "Все типы"},
            value=None,
            label="Тип объекта",
        ).classes("w-full")

        diagrams_container = ui.column().classes("w-full gap-2")
        objects_container = ui.column().classes("w-full gap-2")
        type_options = {}

        async def refresh_types():
            nonlocal type_options

            types = await repo_service.list_types(database_select.value)

            type_options = {
                item.id: item.name
                for item in types
            }

            type_select.options = {
                None: "Все типы",
                **type_options,
            }
            type_select.value = None
            type_select.update()

        async def refresh():
            objects_container.clear()
            database_id = database_select.value

            if not database_id:
                return

            try:
                objects = await repo_service.list_objects(
                    database_id=database_id,
                    type_id=type_select.value,
                    search=search_input.value,
                )
            except RepositoryError as exc:
                show_error(str(exc))
                return

            with objects_container:
                if not objects:
                    ui.label(
                        "В выбранной базе объекты не найдены."
                    ).classes("text-gray-500")
                    return

                for obj in objects:
                    with ui.card().classes("w-full"):
                        with ui.row().classes(
                            "w-full items-center justify-between"
                        ):
                            with ui.column():
                                ui.label(obj.name).classes("font-semibold")
                                ui.label(
                                    obj.type.name if obj.type else ""
                                ).classes("text-sm text-gray-500")

                                if obj.description:
                                    ui.label(obj.description)

                                attributes = obj.attributes or {}

                                if attributes:
                                    ui.label(
                                        f"Атрибутов: {len(attributes)}"
                                    ).classes("text-xs text-blue-600")

                            with ui.row():
                                ui.button(
                                    icon="edit",
                                    on_click=lambda o=obj: open_edit_dialog(o),
                                ).props("flat round")

                                ui.button(
                                    icon="delete",
                                    color="negative",
                                    on_click=lambda o=obj: ask_delete(o),
                                ).props("flat round")

        def open_create_dialog():
            database_id = database_select.value

            if not database_id:
                show_error("Выберите логическую базу")
                return

            if not type_options:
                show_error("Нет доступных типов объектов")
                return

            with ui.dialog() as dialog, ui.card().classes("w-full max-w-xl"):
                ui.label("Новый объект").classes("text-lg font-bold")

                ui.label(
                    "Введите понятное название и выберите тип. "
                    "Например: тип «Документ», название «Заявка на закупку»."
                ).classes("text-sm")

                ui.label(
                    "Описание необязательно. После создания откройте "
                    "карточку объекта кнопкой с карандашом, чтобы "
                    "заполнить дополнительные атрибуты."
                ).classes("text-sm")

                name = ui.input("Название").classes("w-96")

                obj_type = ui.select(
                    type_options,
                    label="Тип объекта",
                ).classes("w-96")

                description = ui.textarea(
                    "Описание"
                ).classes("w-96")

                async def save():
                    try:
                        await repo_service.create_object(
                            database_id=database_id,
                            type_id=obj_type.value,
                            name=name.value,
                            description=description.value,
                            username=user.get("username", "local"),
                            user_id=user.get("id"),
                        )
                    except (RepositoryError, ValueError) as exc:
                        show_error(str(exc))
                        return

                    dialog.close()
                    show_success("Объект создан")
                    await refresh()

                with ui.row():
                    ui.button(
                        "Отмена", on_click=dialog.close
                    ).props("flat")
                    ui.button("Создать", on_click=save)

            dialog.open()

        def open_edit_dialog(obj):
            database_id = database_select.value

            attributes = dict(obj.attributes or {})

            with ui.dialog() as dialog, ui.card().classes(
                "w-full max-w-3xl"
            ):
                ui.label("Карточка объекта").classes(
                    "text-xl font-bold"
                )

                ui.label(
                    f"Тип: {obj.type.name if obj.type else '—'}"
                ).classes("text-sm text-gray-500")

                ui.label(
                    "На вкладке «Основное» изменяются название и описание. "
                    "На вкладке «Атрибуты» можно добавить "
                    "дополнительные сведения."
                ).classes("text-sm")

                ui.label(
                    "Изменения карточки записываются в базу только "
                    "после нажатия «Сохранить объект»."
                ).classes("text-sm")

                with ui.tabs().classes("w-full") as tabs:
                    general_tab = ui.tab("Основное")
                    attributes_tab = ui.tab("Атрибуты")

                with ui.tab_panels(
                    tabs, value=general_tab
                ).classes("w-full"):

                    with ui.tab_panel(general_tab):
                        name = ui.input(
                            "Название",
                            value=obj.name,
                        ).classes("w-full")

                        description = ui.textarea(
                            "Описание",
                            value=obj.description or "",
                        ).classes("w-full")

                        ui.label(f"UUID: {obj.id}").classes(
                            "text-xs text-gray-500"
                        )

                        ui.label(
                            f"Логическая база: "
                            f"{database_options.get(database_id, database_id)}"
                        ).classes("text-sm text-gray-500")

                    with ui.tab_panel(attributes_tab):
                        ui.label(
                            "Дополнительные атрибуты объекта"
                        ).classes("text-lg font-semibold")

                        ui.label(
                            "Атрибут — это дополнительное свойство объекта. "
                            "Например: «Номер документа», «Стоимость» "
                            "или «Дата утверждения»."
                        ).classes("text-sm")

                        ui.label(
                            "Кнопка «Применить» сохраняет атрибут только "
                            "в открытой карточке. Для записи в базу "
                            "нажмите «Сохранить объект»."
                        ).classes("text-sm")

                        attribute_container = ui.column().classes(
                            "w-full gap-2"
                        )

                        def refresh_attributes():
                            attribute_container.clear()

                            with attribute_container:
                                if not attributes:
                                    ui.label(
                                        "Атрибутов пока нет."
                                    ).classes("text-gray-500")

                                for key, value in attributes.items():
                                    with ui.row().classes(
                                        "w-full items-center justify-between"
                                    ):
                                        ui.label(
                                            f"{key}: {attribute_text(value)}"
                                        ).classes("flex-1")

                                        ui.button(
                                            icon="edit",
                                            on_click=lambda k=key:
                                                open_attribute_dialog(k),
                                        ).props("flat round")

                                        ui.button(
                                            icon="delete",
                                            color="negative",
                                            on_click=lambda k=key:
                                                remove_attribute(k),
                                        ).props("flat round")

                        def remove_attribute(key):
                            attributes.pop(key, None)
                            refresh_attributes()

                        def open_attribute_dialog(existing_key=None):
                            existing_value = (
                                attributes.get(existing_key)
                                if existing_key is not None
                                else None
                            )

                            kind, decoded = decode_attribute(existing_value)

                            with ui.dialog() as attribute_dialog, ui.card():
                                ui.label(
                                    "Редактирование атрибута"
                                    if existing_key is not None
                                    else "Новый атрибут"
                                ).classes("text-lg font-semibold")

                                ui.label(
                                    "Укажите название, тип и значение. "
                                    "Например: «Стоимость» — число, "
                                    "«Утверждён» — логическое значение."
                                ).classes("text-sm")

                                ui.label(
                                    "После «Применить» сохраните "
                                    "карточку объекта целиком."
                                ).classes("text-sm")

                                key_input = ui.input(
                                    "Название атрибута",
                                    value=existing_key or "",
                                ).classes("w-80")

                                kind_select = ui.select(
                                    ATTRIBUTE_TYPES,
                                    value=kind,
                                    label="Тип значения",
                                ).classes("w-80")

                                value_container = ui.column().classes(
                                    "w-full"
                                )

                                state = {"input": None}

                                def render_value():
                                    value_container.clear()

                                    with value_container:
                                        selected = kind_select.value

                                        if selected == "boolean":
                                            state["input"] = ui.checkbox(
                                                "Да / Нет",
                                                value=(
                                                    bool(decoded)
                                                    if kind == "boolean"
                                                    else False
                                                ),
                                            )
                                        else:
                                            initial = (
                                                str(decoded)
                                                if selected == kind
                                                and decoded is not None
                                                else ""
                                            )

                                            state["input"] = ui.input(
                                                "Значение",
                                                value=initial,
                                            ).classes("w-80")

                                            if selected == "date":
                                                ui.label(
                                                    "Формат: ГГГГ-ММ-ДД"
                                                ).classes(
                                                    "text-xs text-gray-500"
                                                )

                                kind_select.on_value_change(
                                    lambda _: render_value()
                                )

                                render_value()

                                def save_attribute():
                                    key = (key_input.value or "").strip()

                                    if not key:
                                        show_error(
                                            "Введите название атрибута"
                                        )
                                        return

                                    if (
                                        key != existing_key
                                        and key in attributes
                                    ):
                                        show_error(
                                            "Атрибут с таким названием уже существует"
                                        )
                                        return

                                    try:
                                        encoded = encode_attribute(
                                            kind_select.value,
                                            state["input"].value,
                                        )
                                    except ValueError as exc:
                                        show_error(str(exc))
                                        return

                                    if (
                                        existing_key is not None
                                        and existing_key != key
                                    ):
                                        attributes.pop(existing_key, None)

                                    attributes[key] = encoded

                                    attribute_dialog.close()
                                    refresh_attributes()

                                with ui.row().classes(
                                    "w-full justify-end"
                                ):
                                    ui.button(
                                        "Отмена",
                                        on_click=attribute_dialog.close,
                                    ).props("flat")

                                    ui.button(
                                        "Применить",
                                        on_click=save_attribute,
                                    )

                            attribute_dialog.open()

                        ui.button(
                            "Добавить атрибут",
                            icon="add",
                            on_click=lambda: open_attribute_dialog(),
                        )

                        refresh_attributes()

                async def save_object():
                    try:
                        await repo_service.update_object(
                            database_id=database_id,
                            object_id=obj.id,
                            name=name.value,
                            description=description.value,
                            attributes=attributes,
                            username=user.get("username", "local"),
                            user_id=user.get("id"),
                        )
                    except (RepositoryError, ValueError) as exc:
                        show_error(str(exc))
                        return

                    dialog.close()
                    show_success("Карточка объекта сохранена")
                    await refresh()

                with ui.row().classes("w-full justify-end"):
                    ui.button(
                        "Отмена", on_click=dialog.close
                    ).props("flat")

                    ui.button(
                        "Сохранить объект",
                        on_click=save_object,
                    )

            dialog.open()

        async def ask_delete(obj):
            database_id = database_select.value

            try:
                usages = await repo_service.count_usages(
                    database_id, obj.id
                )
            except RepositoryError as exc:
                show_error(str(exc))
                return

            message = (
                f'Удалить объект "{obj.name}"?'
                f" Связей: {usages['links']}."
                f" Привязок: {usages['models']}."
            )

            async def do_delete():
                try:
                    await repo_service.delete_object(
                        database_id=database_id,
                        object_id=obj.id,
                        username=user.get("username", "local"),
                        user_id=user.get("id"),
                    )
                except RepositoryError as exc:
                    show_error(str(exc))
                    return

                show_success("Объект удалён")
                await refresh()

            confirm_dialog(
                "Удаление объекта",
                message,
                do_delete,
            )

        async def database_changed():
            await refresh_types()
            await refresh()
            await refresh_experimental_diagrams()

        database_select.on_value_change(
            lambda _: database_changed()
        )

        type_select.on_value_change(
            lambda _: refresh()
        )

        search_input.on(
            "keydown.enter",
            lambda _: refresh(),
        )

        # RS_OBJECT_LINKS_PAGE_V10
        async def manage_object_links():
            selected_database = database_select.value

            if not selected_database:
                show_error("Выберите логическую базу")
                return

            await open_object_links_dialog(
                database_id=selected_database,
                database_name=database_options.get(
                    selected_database,
                    selected_database,
                ),
                user=user,
            )

        # RS_OBJECT_TEMPLATES_PAGE_V8
        async def manage_object_templates():
            await open_templates_dialog(user)

        async def create_from_object_template():
            selected_database = database_select.value

            if not selected_database:
                show_error("Выберите логическую базу")
                return

            await open_create_from_template_dialog(
                database_id=selected_database,
                database_name=database_options.get(
                    selected_database,
                    selected_database,
                ),
                user=user,
                on_created=refresh,
            )

        # RS_REPOSITORY_CREATE_MENU_V19
        # RS_EXPERIMENTAL_DIAGRAM_V22
        async def refresh_experimental_diagrams():
            from rubik_studio.ui.pages.experimental_diagrams_v22 import (
                list_experimental_diagrams,
                open_experimental_model,
            )

            selected_database = database_select.value
            diagrams_container.clear()

            if not selected_database:
                return

            try:
                models = await list_experimental_diagrams(
                    selected_database
                )
            except Exception as exc:
                with diagrams_container:
                    ui.label(
                        "Не удалось загрузить экспериментальные диаграммы: "
                        + str(exc)
                    ).classes("text-red-600")
                return

            database_name = database_options.get(
                selected_database,
                str(selected_database),
            )

            with diagrams_container:
                ui.label(
                    "Экспериментальные диаграммы"
                ).classes("text-lg font-semibold")

                if not models:
                    ui.label(
                        "Диаграмм пока нет. Создайте их через "
                        "«Создать… → Диаграмму»."
                    ).classes("text-sm text-gray-500")
                    return

                for model in models:
                    with ui.card().classes("w-full"):
                        with ui.row().classes(
                            "w-full items-center justify-between"
                        ):
                            with ui.column():
                                ui.label(model.name).classes(
                                    "font-semibold"
                                )
                                ui.label(
                                    getattr(model, '_rs_diagram_caption_v43', 'Экспериментальная диаграмма')
                                ).classes("text-sm text-orange-600")

                            ui.button(
                                "Открыть",
                                icon="open_in_new",
                                on_click=lambda m=model, db=selected_database,
                                dn=database_name: open_experimental_model(
                                    db, dn, m.id, m.name
                                ),
                            )

        async def create_diagram():
            selected_database = database_select.value

            if not selected_database:
                show_error("Выберите логическую базу")
                return

            from rubik_studio.ui.pages.experimental_diagrams_v22 import (
                open_create_experimental_dialog,
            )

            async def after_created():
                # Не обновляем список другой базы, если пользователь
                # успел изменить выбор.
                if database_select.value == selected_database:
                    await refresh_experimental_diagrams()

            await open_create_experimental_dialog(
                database_id=selected_database,
                database_name=database_options.get(
                    selected_database,
                    str(selected_database),
                ),
                on_created=after_created,
            )

        with ui.row().classes("items-center"):
            ui.button(
                "Связи объектов",
                icon="link",
                on_click=manage_object_links,
            )

            with ui.button("Трафареты…", icon="view_list"):
                with ui.menu():
                    ui.menu_item(
                        "Трафареты объектов",
                        on_click=manage_object_templates,
                    )
                    ui.menu_item(
                        "Создать объект по трафарету",
                        on_click=create_from_object_template,
                    )

            with ui.button("Создать…", icon="add"):
                with ui.menu():
                    ui.menu_item(
                        "Объект",
                        on_click=open_create_dialog,
                    )
                    ui.menu_item(
                        "Диаграмму",
                        on_click=create_diagram,
                    )

            ui.button(
                "Найти",
                icon="search",
                on_click=refresh,
            ).props("flat")

        await refresh_types()
        await refresh()
        await refresh_experimental_diagrams()
