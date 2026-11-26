# RS_BPMN_SEPARATE_V40_MODULE
# Отдельный экспериментальный тип диаграммы.
# RS_EXPERIMENTAL_DIAGRAM_V22
"""
Экспериментальные диаграммы на полотне V16.

Это не редактор BPMN, VAD или другой нотации.
Служебный тип используется только этим техническим сценарием.
"""

from __future__ import annotations

from nicegui import ui
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from rubik_studio.core.database import get_session_factory
from rubik_studio.core.diagram_storage_v15 import _check_sqlite
from rubik_studio.core.models import (
    Methodology,
    MethodologyModelType,
    Model,
    ModelCategory,
    ModelingDatabase,
    ModelType,
)
from rubik_studio.ui.pages.diagram_editor_v16 import open_model_editor

CATEGORY_CODE = "RS_EXPERIMENTAL"
TYPE_CODE = "RS_BPMN_EXPERIMENTAL_V40"
TYPE_STATUS = "NOT_IMPLEMENTED"  # RS_V22_STATUS_FIX

CATEGORY_NAME = "Экспериментальные диаграммы"
TYPE_NAME = "BPMN 2.0 — экспериментальная"


class ExperimentalDiagramError(Exception):
    pass


def _error_text(exc):
    text = str(exc).strip()
    return text or type(exc).__name__


async def _create_diagram(database_id, name, description):
    """
    Создать экспериментальную модель.

    Категория, тип, разрешение текущей методологии и модель
    создаются в одной транзакции. Обычный сервис создания моделей
    и статусы существующих нотаций не изменяются.
    """
    name = (name or "").strip()
    description = (description or "").strip()

    if not name:
        raise ExperimentalDiagramError("Введите название диаграммы.")

    if len(name) > 500:
        raise ExperimentalDiagramError(
            "Название диаграммы не должно превышать 500 символов."
        )

    if len(description) > 10000:
        raise ExperimentalDiagramError(
            "Описание не должно превышать 10 000 символов."
        )

    factory = get_session_factory()

    try:
        async with factory() as session:
            async with session.begin():
                # До создания модели проверяем, что приложение работает
                # с SQLite и в используемой базе присутствует V14.
                await _check_sqlite(session)

                database = await session.get(
                    ModelingDatabase,
                    database_id,
                )

                if database is None:
                    raise ExperimentalDiagramError(
                        "Выбранная логическая база не найдена."
                    )

                methodology = await session.get(
                    Methodology,
                    database.methodology_id,
                )

                if methodology is None:
                    raise ExperimentalDiagramError(
                        "Методология выбранной базы не найдена."
                    )

                # Этот технический тип разрешаем только для известных
                # встроенных методологий. Не изменяем разрешения нотаций.
                if methodology.code not in {
                    "STANDARD",
                    "EXTENDED",
                    "FULL",
                }:
                    raise ExperimentalDiagramError(
                        "Для этой методологии экспериментальное полотно "
                        "ещё не настроено."
                    )

                result = await session.execute(
                    select(ModelCategory).where(
                        ModelCategory.code == CATEGORY_CODE
                    )
                )
                category = result.scalar_one_or_none()

                if category is None:
                    category = ModelCategory(
                        code=CATEGORY_CODE,
                        name=CATEGORY_NAME,
                        description=(
                            "Технические диаграммы для проверки полотна. "
                            "Не являются готовыми нотациями."
                        ),
                    )
                    session.add(category)
                    await session.flush()
                elif category.name != CATEGORY_NAME:
                    raise ExperimentalDiagramError(
                        "Служебный код категории уже занят. "
                        "Создание отменено."
                    )

                result = await session.execute(
                    select(ModelType).where(
                        ModelType.code == TYPE_CODE
                    )
                )
                model_type = result.scalar_one_or_none()

                if model_type is None:
                    model_type = ModelType(
                        code=TYPE_CODE,
                        name=TYPE_NAME,
                        category_id=category.id,
                        description=(
                            "Экспериментальная диаграмма BPMN 2.0. "
                            "Полная поддержка нотации ещё не реализована."
                        ),
                        keywords="BPMN бизнес-процесс экспериментальная диаграмма",
                        editor_status=TYPE_STATUS,
                        is_system=1,
                    )
                    session.add(model_type)
                    await session.flush()
                elif (
                    model_type.category_id != category.id
                    or model_type.name != TYPE_NAME
                    or model_type.editor_status != TYPE_STATUS
                    or model_type.is_system != 1
                ):
                    raise ExperimentalDiagramError(
                        "Служебный код типа уже занят или изменён. "
                        "Создание отменено."
                    )

                permission = await session.get(
                    MethodologyModelType,
                    (methodology.id, model_type.id),
                )

                if permission is None:
                    session.add(
                        MethodologyModelType(
                            methodology_id=methodology.id,
                            model_type_id=model_type.id,
                        )
                    )
                    await session.flush()

                model = Model(
                    database_id=database.id,
                    model_type_id=model_type.id,
                    name=name,
                    description=description,
                )
                session.add(model)
                await session.flush()

                model_id = model.id
                model_name = model.name

            return model_id, model_name

    except ExperimentalDiagramError:
        raise
    except IntegrityError as exc:
        raise ExperimentalDiagramError(
            "Не удалось создать диаграмму из-за конфликта данных. "
            "Обновите страницу и повторите попытку."
        ) from exc


async def list_experimental_diagrams(database_id):
    """Вернуть только экспериментальные диаграммы выбранной базы."""
    factory = get_session_factory()

    async with factory() as session:
        database = await session.get(ModelingDatabase, database_id)

        if database is None:
            raise ExperimentalDiagramError(
                "Выбранная логическая база не найдена."
            )

        result = await session.execute(
            select(Model)
            .join(ModelType, Model.model_type_id == ModelType.id)
            .where(
                Model.database_id == database_id,
                ModelType.code == TYPE_CODE,
                ModelType.editor_status == TYPE_STATUS,
            )
            .order_by(Model.name, Model.id)
        )

        return list(result.scalars().all())


async def open_create_experimental_dialog(
    database_id,
    database_name,
    on_created=None,
):
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-xl"):
        dialog.props("persistent")

        ui.label("Создать BPMN-диаграмму").classes("text-xl font-bold")
        ui.label(f"Логическая база: {database_name}").classes("text-sm")

        ui.label(
            "Будет создана отдельная экспериментальная BPMN-диаграмма. "
            "Полные правила BPMN 2.0 ещё не реализованы."
        ).classes("text-sm text-orange-600")

        name_input = ui.input(
            "Название диаграммы"
        ).classes("w-full")

        description_input = ui.textarea(
            "Описание — необязательно"
        ).classes("w-full")

        state = {"saving": False}

        async def create():
            if state["saving"]:
                return

            state["saving"] = True
            create_button.disable()

            try:
                model_id, model_name = await _create_diagram(
                    database_id,
                    name_input.value,
                    description_input.value,
                )
            except Exception as exc:
                ui.notify(
                    "Диаграмма не создана: " + _error_text(exc),
                    type="negative",
                    timeout=12000,
                )
                return
            finally:
                state["saving"] = False
                create_button.enable()

            dialog.close()

            ui.notify(
                "Экспериментальная BPMN-диаграмма создана.",
                type="positive",
            )

            if on_created is not None:
                try:
                    await on_created()
                except Exception as exc:
                    ui.notify(
                        "Диаграмма создана, но список не обновлён: "
                        + _error_text(exc),
                        type="warning",
                        timeout=10000,
                    )

            # Даже если открытие не удалось, модель уже создана.
            # Её можно открыть повторно из списка репозитория.
            await open_model_editor(
                database_id=database_id,
                database_name=database_name,
                model_id=model_id,
                model_name=model_name,
            )

        with ui.row().classes("w-full justify-end"):
            ui.button(
                "Отмена",
                on_click=dialog.close,
            ).props("flat")

            create_button = ui.button(
                "Создать",
                icon="add",
                on_click=create,
            )

    dialog.open()


async def open_experimental_model(
    database_id,
    database_name,
    model_id,
    model_name,
):
    await open_model_editor(
        database_id=database_id,
        database_name=database_name,
        model_id=model_id,
        model_name=model_name,
    )
