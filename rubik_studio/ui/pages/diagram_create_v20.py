# RS_DIAGRAM_CREATE_OPEN_V20
"""
Создание и открытие моделей выбранной логической базы.

Создание делегируется modeling_service.create_model.
Экспериментальный редактор не реализует правила нотаций.
"""

from __future__ import annotations

from nicegui import ui

from rubik_studio.core.modeling_databases import (
    ModelingError,
    modeling_service,
)
from rubik_studio.ui.pages.diagram_editor_v16 import open_model_editor


def _text(error):
    result = str(error).strip()
    return result or type(error).__name__


def _status(value):
    # Поддержка обычной строки и Python Enum.
    if hasattr(value, "value"):
        value = value.value
    return str(value).upper()


async def open_create_diagram_dialog(database_id, database_name):
    try:
        types = await modeling_service.search_model_types()
    except Exception as exc:
        ui.notify(
            "Не удалось загрузить каталог диаграмм: " + _text(exc),
            type="negative",
            timeout=10000,
        )
        return

    available = [
        item for item in types
        if _status(item.editor_status) == "AVAILABLE"
    ]

    # Значения select — строки; реальные ID сохраняются отдельно.
    type_by_key = {str(item.id): item for item in available}

    options = {
        key: f"{item.name} ({item.code})"
        for key, item in type_by_key.items()
    }

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-xl"):
        dialog.props("persistent")

        ui.label("Создать диаграмму").classes("text-xl font-bold")
        ui.label(
            f"Логическая база: {database_name}"
        ).classes("text-sm")

        ui.label(
            "При создании сервис дополнительно проверит, "
            "разрешён ли выбранный тип методологией базы."
        ).classes("text-sm")

        if not available:
            ui.label(
                "В каталоге пока нет типов с доступным редактором. "
                "Создание диаграммы сейчас невозможно."
            ).classes("text-orange-600")

            ui.button(
                "Закрыть",
                on_click=dialog.close,
            ).props("flat")

            dialog.open()
            return

        name_input = ui.input(
            "Название диаграммы"
        ).classes("w-full")

        type_select = ui.select(
            options,
            label="Тип диаграммы",
        ).classes("w-full")

        description_input = ui.textarea(
            "Описание — необязательно"
        ).classes("w-full")

        state = {"saving": False}

        async def create():
            if state["saving"]:
                return

            name = (name_input.value or "").strip()
            selected_type = type_by_key.get(str(type_select.value))

            if not name:
                ui.notify("Введите название диаграммы.", type="warning")
                return

            if selected_type is None:
                ui.notify("Выберите тип диаграммы.", type="warning")
                return

            state["saving"] = True
            create_button.disable()

            try:
                await modeling_service.create_model(
                    database_id=database_id,
                    model_type_code=selected_type.code,
                    name=name,
                    description=description_input.value or "",
                )
            except (ModelingError, ValueError) as exc:
                ui.notify(_text(exc), type="negative", timeout=10000)
                return
            except Exception as exc:
                ui.notify(
                    "Не удалось создать диаграмму: " + _text(exc),
                    type="negative",
                    timeout=10000,
                )
                return
            finally:
                state["saving"] = False
                create_button.enable()

            dialog.close()
            ui.notify("Диаграмма создана.", type="positive")

            await open_diagram_list_dialog(database_id, database_name)

        with ui.row().classes("w-full justify-end"):
            ui.button("Отмена", on_click=dialog.close).props("flat")
            create_button = ui.button(
                "Создать",
                icon="add",
                on_click=create,
            )

    dialog.open()


async def open_diagram_list_dialog(database_id, database_name):
    try:
        models = await modeling_service.list_models(database_id)
    except Exception as exc:
        ui.notify(
            "Не удалось загрузить диаграммы базы: " + _text(exc),
            type="negative",
            timeout=10000,
        )
        return

    # Сохраняем настоящие объекты/ID, а в select используем строки.
    model_by_key = {str(model.id): model for model in models}

    options = {
        key: f"{model.name} [{key[:8]}]"
        for key, model in model_by_key.items()
    }

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-xl"):
        dialog.props("persistent")

        ui.label("Диаграммы базы").classes("text-xl font-bold")
        ui.label(
            f"Логическая база: {database_name}"
        ).classes("text-sm")

        ui.label(
            "Открытие здесь использует экспериментальное полотно. "
            "Оно пока не реализует правила нотаций и не показывает линии. "
            "Используйте только тестовые диаграммы."
        ).classes("text-sm text-orange-600")

        if not models:
            ui.label("В этой базе пока нет диаграмм.").classes(
                "text-gray-500"
            )

            with ui.row():
                async def create_first():
                    dialog.close()
                    await open_create_diagram_dialog(
                        database_id,
                        database_name,
                    )

                ui.button(
                    "Создать диаграмму",
                    icon="add",
                    on_click=create_first,
                )
                ui.button(
                    "Закрыть",
                    on_click=dialog.close,
                ).props("flat")

            dialog.open()
            return

        select = ui.select(
            options,
            label="Диаграмма",
        ).classes("w-full")

        async def open_selected():
            model = model_by_key.get(str(select.value))

            if model is None:
                ui.notify("Выберите диаграмму.", type="warning")
                return

            dialog.close()

            await open_model_editor(
                database_id=database_id,
                database_name=database_name,
                model_id=model.id,
                model_name=model.name,
            )

        with ui.row().classes("w-full justify-end"):
            ui.button(
                "Закрыть",
                on_click=dialog.close,
            ).props("flat")

            ui.button(
                "Открыть тестовое полотно",
                icon="open_in_new",
                on_click=open_selected,
            )

    dialog.open()
