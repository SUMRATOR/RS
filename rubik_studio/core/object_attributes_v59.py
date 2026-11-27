# RS_OBJECT_ATTRIBUTE_SCHEMA_V59
"""Наборы атрибутов, зависящие от типа объекта.

Раньше в карточке объекта был один и тот же пустой список и выпадающий
список «Тип значения» из четырёх пунктов. Пользователь справедливо
заметил, что это «топорно»: у документа и у клиента разные свойства, а
человеку приходится вручную придумывать и тип, и название.

Теперь тип объекта определяет набор **полей**. Для каждого поля заранее
известно: подпись, вид значения (текст, дата, файл, выбор) и подсказка.
Пользователь заполняет только значения; «свой» атрибут тоже можно
добавить — он рисуется отдельным блоком.

Модуль намеренно не знает про NiceGUI и базу: это чистые данные и
функции, поэтому правила проверяются тестами без запуска интерфейса.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Виды значений. Совпадают с тем, что уже умеет хранить карточка:
# строка, число, дата, логическое значение и файл (новая ссылка).
KIND_TEXT = "text"
KIND_NUMBER = "number"
KIND_DATE = "date"
KIND_BOOLEAN = "boolean"
KIND_CHOICE = "choice"
KIND_FILE = "file"

KIND_TITLES = {
    KIND_TEXT: "Текст",
    KIND_NUMBER: "Число",
    KIND_DATE: "Дата",
    KIND_BOOLEAN: "Да / Нет",
    KIND_CHOICE: "Выбор из списка",
    KIND_FILE: "Файл",
}


@dataclass(frozen=True)
class AttributeField:
    """Одно поле карточки объекта."""

    key: str
    title: str
    kind: str = KIND_TEXT
    hint: str = ""
    options: tuple[str, ...] = ()
    required: bool = False


@dataclass(frozen=True)
class AttributeSchema:
    """Набор полей для одного типа объекта."""

    code: str
    title: str
    fields: tuple[AttributeField, ...] = ()
    note: str = ""


def _f(key, title, kind=KIND_TEXT, hint="", options=(), required=False):
    return AttributeField(
        key=key,
        title=title,
        kind=kind,
        hint=hint,
        options=tuple(options),
        required=required,
    )


# ── Наборы по типам ────────────────────────────────────────────────────────
# Подписи полей — человеческие, без кодов: они сразу видны в карточке.

DOCUMENT_SCHEMA = AttributeSchema(
    code="DOCUMENT",
    title="Документ",
    note="У документа важны реквизиты и сам файл.",
    fields=(
        _f("doc_number", "Номер документа", hint="Например: 47/2026"),
        _f("doc_date", "Дата документа", KIND_DATE),
        _f(
            "doc_status",
            "Статус",
            KIND_CHOICE,
            options=("Черновик", "На согласовании", "Утверждён", "Архив"),
        ),
        _f("doc_author", "Автор", hint="Кто подготовил документ"),
        _f("doc_file", "Файл документа", KIND_FILE, hint="Ссылка на файл или вложение"),
        _f("doc_valid_until", "Действует до", KIND_DATE),
    ),
)

CUSTOMER_SCHEMA = AttributeSchema(
    code="CUSTOMER",
    title="Клиент",
    note="У клиента — контактные данные и история отношений.",
    fields=(
        _f("full_name", "ФИО", hint="Фамилия Имя Отчество", required=True),
        _f("birth_date", "Дата рождения", KIND_DATE),
        _f("phone", "Телефон", hint="+7 900 000-00-00"),
        _f("email", "Почта", hint="name@example.ru"),
        _f(
            "client_type",
            "Тип клиента",
            KIND_CHOICE,
            options=("Физлицо", "Юрлицо", "ИП"),
        ),
        _f("contract_date", "Дата договора", KIND_DATE),
    ),
)

ORGANIZATION_SCHEMA = AttributeSchema(
    code="ORGANIZATION",
    title="Организация",
    fields=(
        _f("inn", "ИНН", hint="10 или 12 цифр"),
        _f("kpp", "КПП"),
        _f("legal_address", "Юридический адрес"),
        _f("site", "Сайт"),
        _f("registered_at", "Дата регистрации", KIND_DATE),
    ),
)

EMPLOYEE_SCHEMA = AttributeSchema(
    code="EMPLOYEE",
    title="Сотрудник",
    fields=(
        _f("full_name", "ФИО", required=True),
        _f("position_title", "Должность"),
        _f("hired_at", "Дата приёма", KIND_DATE),
        _f("email", "Рабочая почта"),
        _f("phone", "Телефон"),
    ),
)

PROCESS_SCHEMA = AttributeSchema(
    code="PROCESS",
    title="Процесс",
    note="Для процесса важны владелец и границы: когда начинается и заканчивается.",
    fields=(
        _f("process_owner", "Владелец процесса"),
        _f("process_start", "Событие начала"),
        _f("process_end", "Событие завершения"),
        _f("frequency", "Частота выполнения", hint="Например: ежедневно"),
        _f(
            "automation",
            "Уровень автоматизации",
            KIND_CHOICE,
            options=("Ручной", "Частично автоматизирован", "Автоматический"),
        ),
    ),
)

SYSTEM_SCHEMA = AttributeSchema(
    code="SYSTEM",
    title="Система",
    fields=(
        _f("vendor", "Вендор"),
        _f("version", "Версия"),
        _f("url", "Адрес"),
        _f("responsible", "Ответственный"),
        _f("commissioned_at", "Дата ввода", KIND_DATE),
    ),
)

REGULATION_SCHEMA = AttributeSchema(
    code="REGULATION",
    title="Регламент",
    fields=(
        _f("reg_number", "Номер"),
        _f("approved_at", "Дата утверждения", KIND_DATE),
        _f("approved_by", "Утвердил"),
        _f("reg_file", "Файл регламента", KIND_FILE),
        _f("revision", "Редакция"),
    ),
)

RISK_SCHEMA = AttributeSchema(
    code="RISK",
    title="Риск",
    fields=(
        _f("probability", "Вероятность, %", KIND_NUMBER),
        _f("impact", "Влияние, %", KIND_NUMBER),
        _f(
            "risk_level",
            "Уровень",
            KIND_CHOICE,
            options=("Низкий", "Средний", "Высокий", "Критический"),
        ),
        _f("mitigation", "Меры снижения"),
    ),
)

REQUIREMENT_SCHEMA = AttributeSchema(
    code="REQUIREMENT",
    title="Требование",
    fields=(
        _f("req_number", "Номер требования"),
        _f("priority", "Приоритет", KIND_CHOICE, options=("Низкий", "Средний", "Высокий")),
        _f("source", "Источник"),
        _f("accepted", "Принято", KIND_BOOLEAN),
    ),
)

# Типы без собственного набора получают небольшой общий список: он
# осмысленнее пустоты и не мешает добавить своё поле.
GENERIC_SCHEMA = AttributeSchema(
    code="*",
    title="Общие сведения",
    note="Для этого типа отдельный набор не задан — доступны общие поля.",
    fields=(
        _f("code", "Код или обозначение"),
        _f("owner", "Ответственный"),
        _f("source", "Источник"),
        _f("actual_date", "Актуально на", KIND_DATE),
    ),
)

SCHEMAS: dict[str, AttributeSchema] = {
    schema.code: schema
    for schema in (
        DOCUMENT_SCHEMA,
        CUSTOMER_SCHEMA,
        ORGANIZATION_SCHEMA,
        EMPLOYEE_SCHEMA,
        PROCESS_SCHEMA,
        SYSTEM_SCHEMA,
        REGULATION_SCHEMA,
        RISK_SCHEMA,
        REQUIREMENT_SCHEMA,
    )
}


def schema_for(code: str | None) -> AttributeSchema:
    """Набор полей для типа объекта; для неизвестного — общий."""
    if not code:
        return GENERIC_SCHEMA
    return SCHEMAS.get(str(code).upper(), GENERIC_SCHEMA)


def load_fields(code: str | None, existing=None) -> list[AttributeField]:
    """Поля карточки: сначала типовые, затем сохранённые пользователем.

    Уже заполненные «свои» атрибуты не теряются: они идут после типовых,
    поэтому данные старых карточек остаются видимыми и редактируемыми.
    """
    schema = schema_for(code)
    result = list(schema.fields)
    known = {item.key for item in result}

    for key in (existing or {}):
        if key in known:
            continue
        result.append(
            AttributeField(
                key=str(key),
                title=str(key),
                kind=KIND_TEXT,
                hint="Добавлено вручную",
            )
        )
        known.add(key)

    return result


@dataclass
class FieldValues:
    """Значения полей, заполненные пользователем."""

    values: dict = field(default_factory=dict)

    def set(self, key: str, value) -> None:
        self.values[key] = value

    def get(self, key: str, default=None):
        return self.values.get(key, default)


def is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, bool):
        return False
    return False


def missing_required(code: str | None, values: dict) -> list[AttributeField]:
    """Обязательные поля, которые не заполнены.

    Проверка нужна перед сохранением: у клиента ФИО обязательно, иначе
    карточка теряет смысл.
    """
    return [
        item
        for item in schema_for(code).fields
        if item.required and is_empty(values.get(item.key))
    ]


def visible_fields(code: str | None, values: dict | None = None) -> list[AttributeField]:
    """Поля, которые показываем: типовые плюс уже заполненные «свои».

    Пустые «свои» поля не показываем, чтобы карточка не разрасталась.
    """
    values = values or {}
    return [
        item
        for item in load_fields(code, values)
        if item.key in {f.key for f in schema_for(code).fields}
        or not is_empty(values.get(item.key))
    ]
