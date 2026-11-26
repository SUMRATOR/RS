from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from rubik_studio.core.database import get_session_factory
from rubik_studio.core.models import (
    Methodology,
    MethodologyModelType,
    Model,
    ModelCategory,
    ModelingDatabase,
    ModelType,
)


class ModelingError(Exception):
    """Ошибка управления логическими базами."""


class ModelingService:

    async def list_methodologies(self):
        factory = get_session_factory()

        async with factory() as session:
            result = await session.execute(
                select(Methodology).order_by(
                    Methodology.code
                )
            )

            return list(result.scalars().all())

    async def list_databases(self):
        factory = get_session_factory()

        async with factory() as session:
            result = await session.execute(
                select(ModelingDatabase).order_by(
                    ModelingDatabase.name,
                    ModelingDatabase.id,
                )
            )

            return list(result.scalars().all())

    async def get_database(self, database_id: str):
        factory = get_session_factory()

        async with factory() as session:
            database = await session.get(
                ModelingDatabase,
                database_id,
            )

            if database is None:
                raise ModelingError(
                    "Логическая база не найдена"
                )

            return database

    async def create_database(
        self,
        name: str,
        methodology_code: str = "STANDARD",
        description: str | None = None,
    ):
        name = (name or "").strip()

        if not name:
            raise ModelingError(
                "Укажите название логической базы"
            )

        if len(name) > 500:
            raise ModelingError(
                "Название не должно превышать 500 символов"
            )

        methodology_code = (
            methodology_code or ""
        ).strip().upper()

        factory = get_session_factory()

        async with factory() as session:
            result = await session.execute(
                select(Methodology).where(
                    Methodology.code == methodology_code
                )
            )

            methodology = result.scalar_one_or_none()

            if methodology is None:
                raise ModelingError(
                    "Неизвестная методология"
                )

            database = ModelingDatabase(
                name=name,
                description=description,
                methodology_id=methodology.id,
            )

            session.add(database)

            try:
                await session.commit()
                await session.refresh(database)

            except IntegrityError as exc:
                await session.rollback()

                raise ModelingError(
                    "Не удалось создать логическую базу"
                ) from exc

            return database

    async def rename_database(
        self,
        database_id: str,
        new_name: str,
    ):
        new_name = (new_name or "").strip()

        if not new_name:
            raise ModelingError(
                "Название не может быть пустым"
            )

        if len(new_name) > 500:
            raise ModelingError(
                "Название слишком длинное"
            )

        factory = get_session_factory()

        async with factory() as session:
            database = await session.get(
                ModelingDatabase,
                database_id,
            )

            if database is None:
                raise ModelingError(
                    "Логическая база не найдена"
                )

            database.name = new_name

            database.updated_at = (
                datetime.now(UTC)
            )

            await session.commit()

            return database

    async def list_model_categories(self):
        factory = get_session_factory()

        async with factory() as session:
            result = await session.execute(
                select(ModelCategory).order_by(
                    ModelCategory.name
                )
            )

            return list(result.scalars().all())

    async def search_model_types(
        self,
        search: str | None = None,
        category_code: str | None = None,
        methodology_code: str | None = None,
    ):
        factory = get_session_factory()

        async with factory() as session:
            query = select(ModelType).join(
                ModelCategory,
                ModelType.category_id
                == ModelCategory.id,
            )

            if category_code:
                query = query.where(
                    ModelCategory.code
                    == category_code
                )

            if methodology_code:
                query = (
                    query
                    .join(
                        MethodologyModelType,
                        MethodologyModelType.model_type_id
                        == ModelType.id,
                    )
                    .join(
                        Methodology,
                        Methodology.id
                        == MethodologyModelType.methodology_id,
                    )
                    .where(
                        Methodology.code
                        == methodology_code.upper()
                    )
                )

            if search and search.strip():
                term = (
                    "%"
                    + search.strip()
                    .replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                    + "%"
                )

                query = query.where(
                    or_(
                        ModelType.name.ilike(
                            term,
                            escape="\\",
                        ),
                        ModelType.code.ilike(
                            term,
                            escape="\\",
                        ),
                        ModelType.description.ilike(
                            term,
                            escape="\\",
                        ),
                        ModelType.keywords.ilike(
                            term,
                            escape="\\",
                        ),
                        ModelCategory.name.ilike(
                            term,
                            escape="\\",
                        ),
                    )
                )

            query = query.order_by(
                ModelCategory.name,
                ModelType.name,
            )

            result = await session.execute(query)

            return list(result.scalars().all())

    async def list_models(
        self,
        database_id: str,
    ):
        factory = get_session_factory()

        async with factory() as session:
            database = await session.get(
                ModelingDatabase,
                database_id,
            )

            if database is None:
                raise ModelingError(
                    "Логическая база не найдена"
                )

            result = await session.execute(
                select(Model)
                .where(
                    Model.database_id == database_id
                )
                .order_by(Model.name, Model.id)
            )

            return list(result.scalars().all())

    async def create_model(
        self,
        database_id: str,
        model_type_code: str,
        name: str,
        description: str | None = None,
    ):
        name = (name or "").strip()

        if not name:
            raise ModelingError(
                "Укажите название модели"
            )

        if len(name) > 500:
            raise ModelingError(
                "Название модели слишком длинное"
            )

        model_type_code = (
            model_type_code or ""
        ).strip().upper()

        factory = get_session_factory()

        async with factory() as session:
            database = await session.get(
                ModelingDatabase,
                database_id,
            )

            if database is None:
                raise ModelingError(
                    "Логическая база не найдена"
                )

            result = await session.execute(
                select(ModelType).where(
                    ModelType.code == model_type_code
                )
            )

            model_type = result.scalar_one_or_none()

            if model_type is None:
                raise ModelingError(
                    "Неизвестный тип модели"
                )

            permission = await session.execute(
                select(
                    MethodologyModelType.model_type_id
                ).where(
                    MethodologyModelType.methodology_id
                    == database.methodology_id,
                    MethodologyModelType.model_type_id
                    == model_type.id,
                )
            )

            if permission.first() is None:
                raise ModelingError(
                    "Тип модели не разрешён "
                    "выбранной методологией"
                )

            if model_type.editor_status != "AVAILABLE":
                raise ModelingError(
                    "Редактор этого типа модели "
                    "ещё находится в разработке"
                )

            model = Model(
                database_id=database_id,
                model_type_id=model_type.id,
                name=name,
                description=description,
            )

            session.add(model)

            try:
                await session.commit()
                await session.refresh(model)

            except IntegrityError as exc:
                await session.rollback()

                raise ModelingError(
                    "Не удалось сохранить модель"
                ) from exc

            return model


    async def delete_database(self, database_id: str):

        from sqlalchemy import select

        from rubik_studio.core.models import (
            Model,
            ModelElementBinding,
            Object,
            ObjectLink,
            ObjectType,
        )

        factory = get_session_factory()

        async with factory() as session:

            database = await session.get(
                ModelingDatabase,
                database_id,
            )

            if database is None:
                raise ModelingError(
                    "Логическая база не найдена"
                )

            tables = (
                (Model, "моделей"),
                (Object, "объектов"),
                (ObjectLink, "связей"),
                (ModelElementBinding, "привязок"),
                (ObjectType, "пользовательских типов"),
            )

            for model, label in tables:

                count = (
                    await session.execute(
                        select(func.count(model.id)).where(
                            model.database_id == database_id
                        )
                    )
                ).scalar_one()

                if count:
                    raise ModelingError(
                        f"База содержит {count} {label}. "
                        "Удаление запрещено."
                    )

            await session.delete(database)

            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise ModelingError(
                    "База используется другими компонентами"
                ) from exc


modeling_service = ModelingService()

# RS_REPOSITORY_ISOLATION_V3
