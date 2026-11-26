from __future__ import annotations

# RS_OBJECT_TEMPLATES_SERVICE_V8
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from rubik_studio.core.audit_logger import audit
from rubik_studio.core.database import get_session_factory
from rubik_studio.core.models import ObjectTemplate, ObjectType
from rubik_studio.core.repository import RepositoryError, repo_service

FIELD_TYPES = {
    "string": "Строка",
    "number": "Число",
    "date": "Дата",
    "boolean": "Да / Нет",
}


def validate_fields(fields):
    if not isinstance(fields, list):
        raise RepositoryError("Некорректный список полей трафарета")

    if len(fields) > 50:
        raise RepositoryError("В трафарете допускается не более 50 полей")

    result = []
    seen = set()

    for field in fields:
        if not isinstance(field, dict):
            raise RepositoryError("Некорректное поле трафарета")

        name = field.get("name")
        kind = field.get("kind")
        default = field.get("default", "")

        if not isinstance(name, str):
            raise RepositoryError("Введите название поля")

        name = name.strip()

        if not name:
            raise RepositoryError("Введите название поля")

        if len(name) > 200:
            raise RepositoryError(
                "Название поля должно содержать не более 200 символов"
            )

        normalized = name.casefold()

        if normalized in seen:
            raise RepositoryError(
                f'Поле «{name}» указано больше одного раза'
            )

        seen.add(normalized)

        if kind not in FIELD_TYPES:
            raise RepositoryError(
                f'Неизвестный тип поля «{name}»'
            )

        if kind == "boolean":
            if not isinstance(default, bool):
                raise RepositoryError(
                    f'Для поля «{name}» требуется значение Да или Нет'
                )

        else:
            if default is None:
                default = ""

            if not isinstance(default, str):
                default = str(default)

            default = default.strip()

            if len(default) > 10000:
                raise RepositoryError(
                    f'Слишком длинное значение поля «{name}»'
                )

            if default and kind == "number":
                try:
                    number = Decimal(default.replace(",", "."))
                except InvalidOperation as exc:
                    raise RepositoryError(
                        f'Некорректное число в поле «{name}»'
                    ) from exc

                if not number.is_finite():
                    raise RepositoryError(
                        f'Число в поле «{name}» должно быть конечным'
                    )

            if default and kind == "date":
                try:
                    date.fromisoformat(default)
                except ValueError as exc:
                    raise RepositoryError(
                        f'Дата в поле «{name}» должна иметь '
                        'формат ГГГГ-ММ-ДД'
                    ) from exc

        result.append({
            "name": name,
            "kind": kind,
            "default": default,
        })

    return result


def encode_values(fields, values):
    fields = validate_fields(fields)

    if not isinstance(values, dict):
        raise RepositoryError("Некорректные значения полей")

    attributes = {}

    for field in fields:
        name = field["name"]
        kind = field["kind"]
        value = values.get(name, field["default"])

        if kind == "boolean":
            if not isinstance(value, bool):
                raise RepositoryError(
                    f'Для поля «{name}» требуется Да или Нет'
                )

            attributes[name] = value
            continue

        text = str(value if value is not None else "").strip()

        # Пустые необязательные числовые поля и даты не записываются.
        # Строковые поля сохраняются даже при пустом значении.
        if kind == "string":
            attributes[name] = text
            continue

        if not text:
            continue

        if kind == "number":
            try:
                number = Decimal(text.replace(",", "."))
            except InvalidOperation as exc:
                raise RepositoryError(
                    f'Некорректное число в поле «{name}»'
                ) from exc

            if not number.is_finite():
                raise RepositoryError(
                    f'Число в поле «{name}» должно быть конечным'
                )

            if number == number.to_integral_value():
                attributes[name] = int(number)
            else:
                converted = float(number)

                # Исключаем переполнение Python float.
                if converted in (float("inf"), float("-inf")):
                    raise RepositoryError(
                        f'Число в поле «{name}» слишком велико'
                    )

                attributes[name] = converted

        elif kind == "date":
            try:
                date.fromisoformat(text)
            except ValueError as exc:
                raise RepositoryError(
                    f'Дата в поле «{name}» должна иметь '
                    'формат ГГГГ-ММ-ДД'
                ) from exc

            attributes[name] = {
                "__rs_type__": "date",
                "value": text,
            }

    return attributes


async def list_templates():
    factory = get_session_factory()

    async with factory() as session:
        result = await session.execute(
            select(ObjectTemplate)
            .options(selectinload(ObjectTemplate.object_type))
            .order_by(ObjectTemplate.name)
        )
        return list(result.scalars().all())


async def get_template(template_id):
    factory = get_session_factory()

    async with factory() as session:
        result = await session.execute(
            select(ObjectTemplate)
            .options(selectinload(ObjectTemplate.object_type))
            .where(ObjectTemplate.id == template_id)
        )
        return result.scalar_one_or_none()


async def create_template(
    name,
    description,
    type_id,
    fields,
    username="local",
    user_id=None,
):
    if not isinstance(name, str) or not name.strip():
        raise RepositoryError("Введите название трафарета")

    name = name.strip()

    if len(name) > 200:
        raise RepositoryError(
            "Название трафарета должно содержать не более 200 символов"
        )

    description = (description or "").strip()

    if len(description) > 10000:
        raise RepositoryError(
            "Описание трафарета слишком длинное"
        )

    fields = validate_fields(fields)

    factory = get_session_factory()

    async with factory() as session:
        obj_type = await session.get(ObjectType, type_id)

        if (
            obj_type is None
            or not obj_type.is_system
            or obj_type.database_id is not None
        ):
            raise RepositoryError(
                "Для общего трафарета выберите системный тип объекта"
            )

        duplicate = await session.execute(
            select(ObjectTemplate.id).where(
                func.lower(ObjectTemplate.name) == name.lower()
            )
        )

        if duplicate.first():
            raise RepositoryError(
                "Трафарет с таким названием уже существует"
            )

        item = ObjectTemplate(
            name=name,
            description=description,
            type_id=type_id,
            fields=deepcopy(fields),
        )

        session.add(item)

        try:
            await session.commit()
            await session.refresh(item)
        except IntegrityError as exc:
            await session.rollback()
            raise RepositoryError(
                "Не удалось создать трафарет"
            ) from exc

        template_id = item.id
        template_name = item.name

    await audit.log(
        action="CREATE",
        entity_type="ObjectTemplate",
        entity_id=template_id,
        entity_name=template_name,
        username=username,
        user_id=user_id,
        database_id=None,
    )

    return await get_template(template_id)


async def delete_template(
    template_id,
    username="local",
    user_id=None,
):
    factory = get_session_factory()

    async with factory() as session:
        item = await session.get(ObjectTemplate, template_id)

        if item is None:
            raise RepositoryError("Трафарет не найден")

        name = item.name

        await session.delete(item)

        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise RepositoryError(
                "Не удалось удалить трафарет"
            ) from exc

    await audit.log(
        action="DELETE",
        entity_type="ObjectTemplate",
        entity_id=template_id,
        entity_name=name,
        username=username,
        user_id=user_id,
        database_id=None,
    )


async def create_object_from_template(
    database_id,
    template_id,
    name,
    description,
    values,
    username="local",
    user_id=None,
):
    template = await get_template(template_id)

    if template is None:
        raise RepositoryError("Трафарет не найден")

    if (
        template.object_type is None
        or not template.object_type.is_system
        or template.object_type.database_id is not None
    ):
        raise RepositoryError(
            "Системный тип трафарета больше недоступен"
        )

    attributes = encode_values(
        deepcopy(template.fields or []),
        values,
    )

    return await repo_service.create_object(
        database_id=database_id,
        type_id=template.type_id,
        name=name,
        description=description,
        attributes=attributes,
        username=username,
        user_id=user_id,
    )


# RS_TEMPLATE_EDIT_SERVICE_V9

async def update_template(
    template_id,
    name,
    description,
    type_id,
    fields,
    username="local",
    user_id=None,
):
    """Изменяет трафарет, не изменяя созданные по нему объекты."""

    if not isinstance(name, str) or not name.strip():
        raise RepositoryError("Введите название трафарета")

    name = name.strip()

    if len(name) > 200:
        raise RepositoryError(
            "Название трафарета должно содержать не более 200 символов"
        )

    if description is None:
        description = ""

    if not isinstance(description, str):
        raise RepositoryError("Некорректное описание трафарета")

    description = description.strip()

    if len(description) > 10000:
        raise RepositoryError("Описание трафарета слишком длинное")

    fields = validate_fields(fields)

    factory = get_session_factory()

    async with factory() as session:
        item = await session.get(ObjectTemplate, template_id)

        if item is None:
            raise RepositoryError("Трафарет не найден")

        obj_type = await session.get(ObjectType, type_id)

        if (
            obj_type is None
            or not obj_type.is_system
            or obj_type.database_id is not None
        ):
            raise RepositoryError(
                "Для общего трафарета выберите системный тип объекта"
            )

        duplicate = await session.execute(
            select(ObjectTemplate.id).where(
                ObjectTemplate.id != template_id,
                func.lower(ObjectTemplate.name) == name.lower(),
            )
        )

        if duplicate.first():
            raise RepositoryError(
                "Трафарет с таким названием уже существует"
            )

        item.name = name
        item.description = description
        item.type_id = type_id
        item.fields = deepcopy(fields)

        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise RepositoryError(
                "Не удалось сохранить трафарет"
            ) from exc

    await audit.log(
        action="UPDATE",
        entity_type="ObjectTemplate",
        entity_id=template_id,
        entity_name=name,
        username=username,
        user_id=user_id,
        database_id=None,
    )

    return await get_template(template_id)

