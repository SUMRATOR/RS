
from __future__ import annotations

# RS_BPMN_REPOSITORY_FLOWS_V43
from datetime import date
from decimal import Decimal, InvalidOperation

from nicegui import ui

from rubik_studio.auth.middleware import current_user
from rubik_studio.core.object_attributes_v59 import (
    KIND_BOOLEAN,
    KIND_DATE,
    KIND_NUMBER,
    KIND_TEXT,
    KIND_TITLES,
    AttributeField,
    missing_required,
    schema_for,
)
from rubik_studio.core.repository import RepositoryError, repo_service
from rubik_studio.ui.hints_v60 import info_badge
from rubik_studio.ui.layout import (
    confirm_dialog,
    create_page_layout,
    show_error,
    show_success,
)
from rubik_studio.ui.pages.object_links_v10 import (
    open_object_links_dialog,
)
from rubik_studio.ui.pages.object_templates_v8 import (
    open_create_from_template_dialog,
    open_templates_dialog,
)

# RS_NAVIGATION_ATTRIBUTES_V4
# RS_REPOSITORY_HINTS_V7


def object_schema(obj):
    """Набор полей карточки по типу объекта."""
    obj_type = getattr(obj, "type", None)
    return schema_for(getattr(obj_type, "code", None))


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
        # RS_HINT_SYSTEM_V60: вместо трёх абзацев мелкого текста —
        # короткая строка и значок «i» с подробностями.
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.label("Объекты выбранной базы").classes("text-xl font-bold")
            info_badge(
                "Здесь хранятся объекты одной логической базы: процессы, "
                "документы, роли, подразделения. Базы независимы: объекты "
                "не переносятся между ними. Готовые объекты добавляются на "
                "диаграммы этой же базы.",
            )

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

        info_badge(
            "Ниже показаны объекты только этой базы. Переключение базы "
            "не переносит и не удаляет объекты."
        )

        search_input = ui.input(
            "Поиск по названию"
        ).classes("w-full")

        info_badge(
            "Поиск идёт по названию: введите часть названия и нажмите "
            "Enter. Список типов работает как фильтр.",
        )

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
                                edit_button = ui.button(
                                    icon="edit",
                                    on_click=lambda o=obj: open_edit_dialog(o),
                                ).props("flat round")
                                edit_button.mark(f"rs-object-edit-{obj.id}")
                                edit_button.tooltip("Открыть карточку")

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

                with ui.row().classes("items-center gap-2 no-wrap"):
                    ui.label(
                        "Название и тип обязательны, описание — нет."
                    ).classes("text-sm rs-muted")
                    info_badge(
                        "Например: тип «Документ», название «Заявка на "
                        "закупку». После создания нажмите карандаш — "
                        "карточка покажет свойства именно этого типа.",
                    )

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

            # RS_OBJECT_CARD_SCROLL_V60
            # Карточка не помещалась в окно: нижние поля («Дата документа»,
            # «Файл документа») обрезались, а прокрутки не было — до них
            # нельзя было добраться. Ограничиваем высоту карточки, а
            # панели вкладок прокручиваем.
            with ui.dialog() as dialog, ui.card().classes(
                "w-full max-w-3xl rs-object-card"
            ).style(
                "max-height: calc(100vh - 96px); display: flex; "
                "flex-direction: column; gap: 8px;"
            ):
                ui.label("Карточка объекта").classes(
                    "text-xl font-bold"
                )

                ui.label(
                    f"Тип: {obj.type.name if obj.type else '—'}"
                ).classes("text-sm text-gray-500")

                # RS_CARD_HEADER_COMPACT_V60
                # Две длинные подсказки занимали пол-экрана и вытесняли
                # поля вниз. Оставили одну короткую строку и значок «i».
                with ui.row().classes("items-center gap-1 no-wrap"):
                    ui.label(
                        "Изменения запишутся после «Сохранить объект»."
                    ).classes("text-sm rs-muted")
                    info_badge(
                        "Вкладка «Основное» — название и описание. "
                        "Вкладка «Атрибуты» — свойства, зависящие от типа "
                        "объекта: у документа реквизиты и файл, у клиента "
                        "ФИО и дата рождения."
                    )

                with ui.tabs().classes("w-full") as tabs:
                    general_tab = ui.tab("Основное")
                    attributes_tab = ui.tab("Атрибуты")

                with ui.tab_panels(
                    tabs, value=general_tab
                ).classes("w-full").style(
                    # Прокрутка внутри вкладки: кнопки «Отмена» и
                    # «Сохранить объект» остаются на виду.
                    "flex: 1 1 auto; min-height: 0; overflow-y: auto; "
                    "overflow-x: hidden; padding-right: 6px;"
                ).mark("rs-object-card-scroll"):

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
                        # RS_OBJECT_ATTRIBUTE_SCHEMA_V59
                        # Набор полей зависит от типа объекта: у документа
                        # реквизиты и файл, у клиента ФИО и дата рождения.
                        # Вместо «придумай название и выбери тип значения»
                        # пользователь видит готовый список свойств.
                        schema = object_schema(obj)
                        widgets: dict[str, object] = {}

                        ui.label(schema.title).classes("text-lg font-semibold")

                        if schema.note:
                            ui.label(schema.note).classes("text-sm rs-muted")

                        ui.label(
                            "Пустые поля не сохраняются — карточка остаётся "
                            "компактной. Своё свойство можно добавить внизу."
                        ).classes("text-sm rs-muted")

                        attribute_container = ui.column().classes("w-full gap-2")

                        def field_value(item):
                            """Текущее значение поля из карточки."""
                            raw = attributes.get(item.key)
                            kind, decoded = decode_attribute(raw)
                            return raw, kind, decoded

                        def make_widget(item, raw, _kind, decoded):
                            """Поле ввода под вид значения."""
                            if item.kind == "date":
                                return ui.input(
                                    "ГГГГ-ММ-ДД",
                                    value="" if raw is None else str(decoded),
                                ).classes("w-full")

                            if item.kind == "boolean":
                                return ui.checkbox("Да", value=bool(decoded))

                            if item.kind == "choice":
                                return ui.select(
                                    list(item.options),
                                    value=(
                                        str(decoded)
                                        if raw is not None
                                        and str(decoded) in item.options
                                        else None
                                    ),
                                    label="Выберите значение",
                                ).classes("w-full")

                            if item.kind == "number":
                                return ui.input(
                                    "Число",
                                    value="" if raw is None else str(decoded),
                                ).classes("w-full")

                            if item.kind == "file":
                                return ui.input(
                                    "Ссылка на файл",
                                    value="" if raw is None else str(decoded),
                                ).classes("w-full")

                            return ui.input(
                                "Значение",
                                value="" if raw is None else str(decoded),
                            ).classes("w-full")

                        def show_file_link(raw):
                            """Показываем, что файл прикреплён."""
                            if not raw:
                                return
                            text = str(raw).strip()
                            if not text:
                                return
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("attach_file")
                                ui.link(text, text, new_tab=True).classes("text-sm")

                        def attribute_row(item, is_custom=False):
                            """Одна строка карточки: подпись, подсказка, поле."""
                            raw, kind, decoded = field_value(item)

                            with ui.column().classes("w-full gap-1"):
                                with ui.row().classes(
                                    "w-full items-center justify-between no-wrap"
                                ):
                                    caption = ui.label(
                                        item.title
                                        + (" *" if item.required else "")
                                    ).classes("text-sm font-semibold")

                                    caption.tooltip(
                                        f"Вид значения: {KIND_TITLES.get(item.kind, item.kind)}"
                                    )

                                    if is_custom:
                                        ui.button(
                                            icon="close",
                                            on_click=lambda k=item.key: (
                                                attributes.pop(k, None),
                                                refresh_attributes(),
                                            ),
                                        ).props("flat round dense").tooltip(
                                            "Удалить своё свойство"
                                        )

                                if item.hint:
                                    ui.label(item.hint).classes("text-xs rs-muted")

                                widgets[item.key] = make_widget(
                                    item, raw, kind, decoded
                                )

                                if item.kind == "file":
                                    show_file_link(raw)

                        def refresh_attributes():
                            widgets.clear()
                            attribute_container.clear()

                            with attribute_container:
                                for item in schema.fields:
                                    attribute_row(item)

                                schema_keys = {f.key for f in schema.fields}
                                extra = [
                                    key
                                    for key in attributes
                                    if key not in schema_keys
                                ]

                                if extra:
                                    ui.separator()
                                    ui.label(
                                        "Свои свойства — добавлены вручную"
                                    ).classes("text-sm font-semibold")

                                    for key in extra:
                                        attribute_row(
                                            AttributeField(
                                                key=key,
                                                title=key,
                                                kind="string",
                                            ),
                                            is_custom=True,
                                        )

                        def read_widget(item, widget):
                            """Значение поля в том виде, что хранит карточка."""
                            if item.kind == "date":
                                text = str(widget.value or "").strip()
                                if not text:
                                    return None
                                return encode_attribute("date", text)

                            if item.kind == "boolean":
                                return bool(widget.value)

                            if item.kind == "number":
                                text = str(widget.value or "").strip()
                                if not text:
                                    return None
                                return encode_attribute("number", text)

                            return str(widget.value or "").strip()

                        def collect_values():
                            """Собрать значения полей; ошибки — с названием поля."""
                            collected = {}

                            for item in schema.fields:
                                widget = widgets.get(item.key)
                                if widget is None:
                                    continue

                                try:
                                    collected[item.key] = read_widget(item, widget)
                                except ValueError as exc:
                                    raise ValueError(
                                        f"{item.title}: {exc}"
                                    ) from exc

                            for key, widget in list(widgets.items()):
                                if key in collected:
                                    continue
                                value = str(getattr(widget, "value", "") or "").strip()
                                collected[key] = value

                            return collected

                        refresh_attributes()

                        def open_attribute_dialog():
                            """Своё свойство: название и вид значения."""
                            with ui.dialog() as attribute_dialog, ui.card():
                                ui.label("Своё свойство").classes(
                                    "text-lg font-semibold"
                                )

                                ui.label(
                                    "Для полей, которых нет в наборе типа. "
                                    "Например: «Внутренний код»."
                                ).classes("text-sm rs-muted")

                                key_input = ui.input(
                                    "Название"
                                ).classes("w-full")

                                kind_select = ui.select(
                                    {
                                        KIND_TEXT: KIND_TITLES[KIND_TEXT],
                                        KIND_NUMBER: KIND_TITLES[KIND_NUMBER],
                                        KIND_DATE: KIND_TITLES[KIND_DATE],
                                        KIND_BOOLEAN: KIND_TITLES[KIND_BOOLEAN],
                                    },
                                    value=KIND_TEXT,
                                    label="Вид значения",
                                ).classes("w-full")

                                value_container = ui.column().classes("w-full")

                                def render_value():
                                    value_container.clear()
                                    with value_container:
                                        if kind_select.value == KIND_BOOLEAN:
                                            ui.checkbox("Да")
                                        else:
                                            placeholder = (
                                                "ГГГГ-ММ-ДД"
                                                if kind_select.value == KIND_DATE
                                                else "Значение"
                                            )
                                            ui.input(placeholder).classes("w-full")

                                kind_select.on_value_change(
                                    lambda _e: render_value()
                                )
                                render_value()

                                def save_attribute():
                                    key = (key_input.value or "").strip()

                                    if not key:
                                        show_error("Введите название свойства")
                                        return

                                    if key in schema.fields or key in attributes:
                                        show_error(
                                            "Свойство с таким названием уже есть"
                                        )
                                        return

                                    # Своё свойство хранится как текст: этого
                                    # достаточно, чтобы не потерять значение.
                                    attributes[key] = ""
                                    attribute_dialog.close()
                                    refresh_attributes()

                                with ui.row().classes("w-full justify-end"):
                                    ui.button(
                                        "Отмена",
                                        on_click=attribute_dialog.close,
                                    ).props("flat")

                                    ui.button(
                                        "Добавить",
                                        on_click=save_attribute,
                                    )

                            attribute_dialog.open()

                        ui.button(
                            "Добавить своё свойство",
                            icon="add",
                            on_click=open_attribute_dialog,
                        ).props("flat")

                async def save_object():
                    try:
                        values = collect_values()
                    except ValueError as exc:
                        show_error(str(exc))
                        return

                    # Пустые поля не записываем: карточка не разрастается.
                    filled = {
                        key: value
                        for key, value in values.items()
                        if value not in (None, "")
                    }

                    missing = missing_required(
                        getattr(getattr(obj, "type", None), "code", None),
                        filled,
                    )
                    if missing:
                        show_error(
                            "Заполните обязательные поля: "
                            + ", ".join(item.title for item in missing)
                        )
                        return

                    try:
                        await repo_service.update_object(
                            database_id=database_id,
                            object_id=obj.id,
                            name=name.value,
                            description=description.value,
                            attributes=filled,
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
