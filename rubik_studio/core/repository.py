from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from rubik_studio.core.audit_logger import audit
from rubik_studio.core.database import get_session_factory
from rubik_studio.core.models import (
    ModelElementBinding,
    ModelingDatabase,
    Object,
    ObjectLink,
    ObjectType,
)
from rubik_studio.core.validators import (
    validate_description,
    validate_link,
    validate_object_name,
)


class RepositoryError(Exception):
    pass


class RepositoryService:

    async def _check_database(self, session, database_id):
        if not database_id:
            raise RepositoryError(
                "Выберите логическую базу"
            )

        database = await session.get(
            ModelingDatabase,
            database_id,
        )

        if database is None:
            raise RepositoryError(
                "Логическая база не найдена"
            )

        return database

    async def list_databases(self):
        factory = get_session_factory()

        async with factory() as session:
            result = await session.execute(
                select(ModelingDatabase).order_by(
                    ModelingDatabase.name
                )
            )
            return list(result.scalars().all())

    async def list_types(self, database_id=None):
        factory = get_session_factory()

        async with factory() as session:
            if database_id:
                await self._check_database(
                    session, database_id
                )

            query = select(ObjectType)

            if database_id:
                query = query.where(
                    or_(
                        ObjectType.is_system.is_(True),
                        ObjectType.database_id == database_id,
                    )
                )
            else:
                query = query.where(
                    ObjectType.is_system.is_(True)
                )

            result = await session.execute(
                query.order_by(ObjectType.name)
            )

            return list(result.scalars().all())

    async def get_type(self, type_id, database_id=None):
        factory = get_session_factory()

        async with factory() as session:
            obj_type = await session.get(
                ObjectType, type_id
            )

            if obj_type is None:
                return None

            if obj_type.is_system:
                return obj_type

            if (
                database_id
                and obj_type.database_id == database_id
            ):
                return obj_type

            return None

    async def list_objects(
        self,
        database_id,
        type_id=None,
        search=None,
    ):
        factory = get_session_factory()

        async with factory() as session:
            await self._check_database(
                session, database_id
            )

            query = (
                select(Object)
                .options(selectinload(Object.type))
                .where(Object.database_id == database_id)
            )

            if type_id:
                query = query.where(
                    Object.type_id == type_id
                )

            if search:
                query = query.where(
                    Object.name.ilike(
                        "%" + search.strip() + "%"
                    )
                )

            result = await session.execute(
                query.order_by(Object.name)
            )

            return list(result.scalars().all())

    async def get_object(
        self,
        database_id,
        object_id,
    ):
        factory = get_session_factory()

        async with factory() as session:
            result = await session.execute(
                select(Object)
                .options(selectinload(Object.type))
                .where(
                    Object.id == object_id,
                    Object.database_id == database_id,
                )
            )

            return result.scalar_one_or_none()

    async def create_object(
        self,
        database_id,
        type_id,
        name,
        description="",
        attributes=None,
        username="local",
        user_id=None,
    ):
        valid, message = validate_object_name(name)

        if not valid:
            raise RepositoryError(message)

        valid, message = validate_description(
            description or ""
        )

        if not valid:
            raise RepositoryError(message)

        factory = get_session_factory()

        async with factory() as session:
            await self._check_database(
                session, database_id
            )

            obj_type = await session.get(
                ObjectType, type_id
            )

            if obj_type is None:
                raise RepositoryError(
                    "Неизвестный тип объекта"
                )

            if (
                not obj_type.is_system
                and obj_type.database_id != database_id
            ):
                raise RepositoryError(
                    "Тип объекта принадлежит другой базе"
                )

            normalized = name.strip()

            result = await session.execute(
                select(Object).where(
                    Object.database_id == database_id,
                    Object.type_id == type_id,
                    func.lower(Object.name)
                    == normalized.lower(),
                )
            )

            if result.first():
                raise RepositoryError(
                    "Объект с таким названием уже существует"
                )

            obj = Object(
                database_id=database_id,
                type_id=type_id,
                name=normalized,
                description=description or "",
                attributes=attributes or {},
            )

            session.add(obj)

            try:
                await session.commit()
                await session.refresh(obj)
            except IntegrityError as exc:
                await session.rollback()
                raise RepositoryError(
                    "Не удалось создать объект"
                ) from exc

        await audit.log(
            action="CREATE",
            entity_type="Object",
            entity_id=obj.id,
            entity_name=obj.name,
            username=username,
            user_id=user_id,
            database_id=database_id,
        )

        return obj

    async def update_object(
        self,
        database_id,
        object_id,
        name=None,
        description=None,
        attributes=None,
        username="local",
        user_id=None,
    ):
        factory = get_session_factory()

        async with factory() as session:
            await self._check_database(
                session, database_id
            )

            obj = await session.get(
                Object, object_id
            )

            if (
                obj is None
                or obj.database_id != database_id
            ):
                raise RepositoryError(
                    "Объект не найден в выбранной базе"
                )

            if name is not None:
                valid, message = validate_object_name(
                    name
                )

                if not valid:
                    raise RepositoryError(message)

                normalized = name.strip()

                duplicate = await session.execute(
                    select(Object.id).where(
                        Object.database_id == database_id,
                        Object.type_id == obj.type_id,
                        Object.id != object_id,
                        func.lower(Object.name)
                        == normalized.lower(),
                    )
                )

                if duplicate.first():
                    raise RepositoryError(
                        "Объект с таким названием уже существует"
                    )

                obj.name = normalized

            if description is not None:
                valid, message = validate_description(
                    description
                )

                if not valid:
                    raise RepositoryError(message)

                obj.description = description

            if attributes is not None:
                obj.attributes = attributes

            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise RepositoryError(
                    "Не удалось сохранить изменения"
                ) from exc

            result_name = obj.name

        await audit.log(
            action="UPDATE",
            entity_type="Object",
            entity_id=object_id,
            entity_name=result_name,
            username=username,
            user_id=user_id,
            database_id=database_id,
        )

        return await self.get_object(
            database_id, object_id
        )

    async def count_usages(
        self,
        database_id,
        object_id,
    ):
        factory = get_session_factory()

        async with factory() as session:
            obj = await session.get(
                Object, object_id
            )

            if (
                obj is None
                or obj.database_id != database_id
            ):
                raise RepositoryError(
                    "Объект не найден"
                )

            links = await session.execute(
                select(func.count(ObjectLink.id)).where(
                    ObjectLink.database_id == database_id,
                    or_(
                        ObjectLink.source_id == object_id,
                        ObjectLink.target_id == object_id,
                    ),
                )
            )

            bindings = await session.execute(
                select(
                    func.count(ModelElementBinding.id)
                ).where(
                    ModelElementBinding.database_id
                    == database_id,
                    ModelElementBinding.object_id
                    == object_id,
                )
            )

            return {
                "links": links.scalar_one(),
                "models": bindings.scalar_one(),
            }

    async def delete_object(
        self,
        database_id,
        object_id,
        username="local",
        user_id=None,
    ):
        factory = get_session_factory()

        async with factory() as session:
            obj = await session.get(
                Object, object_id
            )

            if (
                obj is None
                or obj.database_id != database_id
            ):
                raise RepositoryError(
                    "Объект не найден в выбранной базе"
                )

            name = obj.name

            await session.delete(obj)

            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise RepositoryError(
                    "Объект используется в моделях или связях"
                ) from exc

        await audit.log(
            action="DELETE",
            entity_type="Object",
            entity_id=object_id,
            entity_name=name,
            username=username,
            user_id=user_id,
            database_id=database_id,
        )

    async def list_links(
        self,
        database_id,
        object_id=None,
    ):
        factory = get_session_factory()

        async with factory() as session:
            await self._check_database(
                session, database_id
            )

            query = select(ObjectLink).where(
                ObjectLink.database_id == database_id
            )

            if object_id:
                query = query.where(
                    or_(
                        ObjectLink.source_id == object_id,
                        ObjectLink.target_id == object_id,
                    )
                )

            result = await session.execute(query)

            return list(result.scalars().all())

    async def create_link(
        self,
        database_id,
        source_id,
        target_id,
        link_type,
        attributes=None,
        username="local",
        user_id=None,
    ):
        valid, message = validate_link(
            source_id, target_id
        )

        if not valid:
            raise RepositoryError(message)

        factory = get_session_factory()

        async with factory() as session:
            await self._check_database(
                session, database_id
            )

            source = await session.get(
                Object, source_id
            )

            target = await session.get(
                Object, target_id
            )

            if source is None or target is None:
                raise RepositoryError(
                    "Один из объектов не найден"
                )

            if (
                source.database_id != database_id
                or target.database_id != database_id
            ):
                raise RepositoryError(
                    "Нельзя связывать объекты из разных баз"
                )

            existing = await session.execute(
                select(ObjectLink).where(
                    ObjectLink.database_id == database_id,
                    ObjectLink.source_id == source_id,
                    ObjectLink.target_id == target_id,
                    ObjectLink.link_type == link_type,
                )
            )

            if existing.first():
                raise RepositoryError(
                    "Такая связь уже существует"
                )

            link = ObjectLink(
                database_id=database_id,
                source_id=source_id,
                target_id=target_id,
                link_type=link_type,
                attributes=attributes or {},
            )

            session.add(link)

            try:
                await session.commit()
                await session.refresh(link)
            except IntegrityError as exc:
                await session.rollback()
                raise RepositoryError(
                    "Не удалось создать связь"
                ) from exc

        await audit.log(
            action="CREATE_LINK",
            entity_type="ObjectLink",
            entity_id=link.id,
            username=username,
            user_id=user_id,
            database_id=database_id,
        )

        return link

    async def delete_link(
        self,
        database_id,
        link_id,
        username="local",
        user_id=None,
    ):
        factory = get_session_factory()

        async with factory() as session:
            link = await session.get(
                ObjectLink, link_id
            )

            if (
                link is None
                or link.database_id != database_id
            ):
                raise RepositoryError(
                    "Связь не найдена"
                )

            await session.delete(link)
            await session.commit()

        await audit.log(
            action="DELETE_LINK",
            entity_type="ObjectLink",
            entity_id=link_id,
            username=username,
            user_id=user_id,
            database_id=database_id,
        )


    # RS_CUSTOM_OBJECT_TYPES_V6

    @staticmethod
    def _validate_custom_type_values(name, color):
        import re

        if not isinstance(name, str):
            raise RepositoryError("Введите название типа")

        name = name.strip()

        if not name:
            raise RepositoryError("Введите название типа")

        if len(name) > 200:
            raise RepositoryError(
                "Название типа должно содержать не более 200 символов"
            )

        if not isinstance(color, str):
            raise RepositoryError(
                "Цвет должен иметь формат #RRGGBB"
            )

        color = color.strip().upper()

        if not re.fullmatch(r"#[0-9A-F]{6}", color):
            raise RepositoryError(
                "Цвет должен иметь формат #RRGGBB"
            )

        return name, color

    async def create_custom_type(
        self,
        database_id,
        name,
        color="#9E9E9E",
        username="local",
        user_id=None,
    ):
        import uuid

        name, color = self._validate_custom_type_values(
            name, color
        )

        factory = get_session_factory()

        async with factory() as session:
            await self._check_database(session, database_id)

            # Код уникален во всей физической БД.
            # Пользователь его не вводит.
            code = "USER_" + uuid.uuid4().hex.upper()

            obj_type = ObjectType(
                code=code,
                name=name,
                icon="category",
                color=color,
                database_id=database_id,
                is_system=False,
            )

            session.add(obj_type)

            try:
                await session.commit()
                await session.refresh(obj_type)
            except IntegrityError as exc:
                await session.rollback()
                raise RepositoryError(
                    "Не удалось создать тип объекта"
                ) from exc

            type_id = obj_type.id
            result_name = obj_type.name

        await audit.log(
            action="CREATE",
            entity_type="ObjectType",
            entity_id=type_id,
            entity_name=result_name,
            username=username,
            user_id=user_id,
            database_id=database_id,
        )

        return obj_type

    async def update_custom_type(
        self,
        database_id,
        type_id,
        name,
        color,
        username="local",
        user_id=None,
    ):
        from sqlalchemy import update

        name, color = self._validate_custom_type_values(
            name, color
        )

        factory = get_session_factory()

        async with factory() as session:
            await self._check_database(session, database_id)

            # Код, database_id и is_system не изменяются.
            statement = (
                update(ObjectType)
                .where(
                    ObjectType.id == type_id,
                    ObjectType.database_id == database_id,
                    ObjectType.is_system.is_(False),
                )
                .values(
                    name=name,
                    color=color,
                )
            )

            try:
                result = await session.execute(statement)

                if result.rowcount != 1:
                    await session.rollback()
                    raise RepositoryError(
                        "Пользовательский тип не найден "
                        "в выбранной базе"
                    )

                await session.commit()

            except IntegrityError as exc:
                await session.rollback()
                raise RepositoryError(
                    "Не удалось изменить тип объекта"
                ) from exc

        await audit.log(
            action="UPDATE",
            entity_type="ObjectType",
            entity_id=type_id,
            entity_name=name,
            username=username,
            user_id=user_id,
            database_id=database_id,
        )

        return await self.get_type(type_id, database_id)

    async def count_custom_type_objects(
        self,
        database_id,
        type_id,
    ):
        factory = get_session_factory()

        async with factory() as session:
            await self._check_database(session, database_id)

            obj_type = await session.get(ObjectType, type_id)

            if (
                obj_type is None
                or obj_type.is_system
                or obj_type.database_id != database_id
            ):
                raise RepositoryError(
                    "Пользовательский тип не найден "
                    "в выбранной базе"
                )

            result = await session.execute(
                select(func.count(Object.id)).where(
                    Object.type_id == type_id
                )
            )

            return result.scalar_one()

    async def delete_custom_type(
        self,
        database_id,
        type_id,
        username="local",
        user_id=None,
    ):
        from sqlalchemy import delete, exists

        factory = get_session_factory()

        async with factory() as session:
            await self._check_database(session, database_id)

            obj_type = await session.get(ObjectType, type_id)

            if (
                obj_type is None
                or obj_type.is_system
                or obj_type.database_id != database_id
            ):
                raise RepositoryError(
                    "Пользовательский тип не найден "
                    "в выбранной базе"
                )

            type_name = obj_type.name

            # Проверка использования включена в DELETE.
            # Внешний ключ также защищает используемые типы.
            used = exists(
                select(Object.id).where(
                    Object.type_id == type_id
                )
            )

            statement = (
                delete(ObjectType)
                .where(
                    ObjectType.id == type_id,
                    ObjectType.database_id == database_id,
                    ObjectType.is_system.is_(False),
                    ~used,
                )
                .execution_options(synchronize_session=False)
            )

            try:
                result = await session.execute(statement)

                if result.rowcount != 1:
                    await session.rollback()
                    raise RepositoryError(
                        "Тип используется объектами или уже удалён"
                    )

                await session.commit()

            except IntegrityError as exc:
                await session.rollback()
                raise RepositoryError(
                    "Тип используется объектами и не может быть удалён"
                ) from exc

        await audit.log(
            action="DELETE",
            entity_type="ObjectType",
            entity_id=type_id,
            entity_name=type_name,
            username=username,
            user_id=user_id,
            database_id=database_id,
        )


repo_service = RepositoryService()

# RS_REPOSITORY_ISOLATION_V3
