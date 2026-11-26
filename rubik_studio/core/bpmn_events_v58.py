# RS_BPMN_EVENT_VARIANTS_V58
"""Варианты событий BPMN: положение + подтип + «поймать/выбросить».

В BPMN событие описывается тремя вещами:

1. **положение** — начальное, промежуточное, граничное или конечное;
2. **подтип** — что именно произошло: сообщение, таймер, ошибка …
3. **поведение** — для промежуточных: ждём событие (catch) или
   сообщаем о нём (throw).

В палитре V55 все события уже лежат константами. Но подбор по одному
из сорока символов неудобен: пользователь думает «нужно промежуточное
ожидание по времени», а не «код INTERMEDIATE_TIMER».

Здесь строится таблица совместимости: какие подтипы допустимы для какого
положения. По ней интерфейс показывает вкладки и не даёт собрать
несуществующее в нотации событие. Код символа остаётся прежним, поэтому
сохранённые диаграммы открываются без миграции.

Модуль не импортирует NiceGUI — его можно проверять автотестами.
"""

from __future__ import annotations

from dataclasses import dataclass

from rubik_studio.core.bpmn_catalog_v55 import CATALOG

# ── Положения событий ──────────────────────────────────────────────────────

POSITION_START = "start"
POSITION_INTERMEDIATE = "intermediate"
POSITION_BOUNDARY = "boundary"
POSITION_END = "end"

POSITION_ORDER = (
    POSITION_START,
    POSITION_INTERMEDIATE,
    POSITION_BOUNDARY,
    POSITION_END,
)

POSITION_TITLES = {
    POSITION_START: "Начальное",
    POSITION_INTERMEDIATE: "Промежуточное",
    POSITION_BOUNDARY: "Граничное",
    POSITION_END: "Конечное",
}

POSITION_HINTS = {
    POSITION_START: "С него начинается процесс",
    POSITION_INTERMEDIATE: "Происходит по ходу процесса",
    POSITION_BOUNDARY: "Крепится к границе задачи или подпроцесса",
    POSITION_END: "Им процесс заканчивается",
}

# ── Подтипы событий ───────────────────────────────────────────────────────
# Ключ — внутренний код подтипа. Значения: код символа в CATALOG и русское
# название, которое видит пользователь.

SUBTYPE_PLAIN = "plain"
SUBTYPE_MESSAGE = "message"
SUBTYPE_TIMER = "timer"
SUBTYPE_CONDITIONAL = "conditional"
SUBTYPE_SIGNAL = "signal"
SUBTYPE_ERROR = "error"
SUBTYPE_ESCALATION = "escalation"
SUBTYPE_COMPENSATION = "compensation"
SUBTYPE_LINK = "link"
SUBTYPE_TERMINATE = "terminate"
SUBTYPE_CANCEL = "cancel"
SUBTYPE_MULTIPLE = "multiple"
SUBTYPE_PARALLEL_MULTIPLE = "parallel_multiple"

# Коды символов совместимости: положение + подтип → код в каталоге V55.
# Отсутствие пары означает, что такого события в BPMN 2.0 нет.
COMPATIBILITY: dict[str, dict[str, str]] = {
    POSITION_START: {
        SUBTYPE_PLAIN: "START_EVENT",
        SUBTYPE_MESSAGE: "START_MESSAGE",
        SUBTYPE_TIMER: "START_TIMER",
        SUBTYPE_CONDITIONAL: "START_CONDITIONAL",
        SUBTYPE_SIGNAL: "START_SIGNAL",
        SUBTYPE_ERROR: "START_ERROR",
        SUBTYPE_MULTIPLE: "START_MULTIPLE",
        SUBTYPE_PARALLEL_MULTIPLE: "START_PARALLEL_MULTIPLE",
    },
    POSITION_INTERMEDIATE: {
        SUBTYPE_PLAIN: "INTERMEDIATE_EVENT",
        SUBTYPE_MESSAGE: "INTERMEDIATE_MESSAGE",
        SUBTYPE_TIMER: "INTERMEDIATE_TIMER",
        SUBTYPE_ESCALATION: "INTERMEDIATE_ESCALATION",
        SUBTYPE_CONDITIONAL: "INTERMEDIATE_CONDITIONAL",
        SUBTYPE_LINK: "INTERMEDIATE_LINK",
        SUBTYPE_SIGNAL: "INTERMEDIATE_SIGNAL",
        SUBTYPE_ERROR: "INTERMEDIATE_ERROR",
        SUBTYPE_COMPENSATION: "INTERMEDIATE_COMPENSATION",
        SUBTYPE_MULTIPLE: "INTERMEDIATE_MULTIPLE",
        SUBTYPE_PARALLEL_MULTIPLE: "INTERMEDIATE_PARALLEL_MULTIPLE",
    },
    POSITION_BOUNDARY: {
        SUBTYPE_MESSAGE: "BOUNDARY_MESSAGE",
        SUBTYPE_TIMER: "BOUNDARY_TIMER",
        SUBTYPE_ESCALATION: "BOUNDARY_ESCALATION",
        SUBTYPE_CONDITIONAL: "BOUNDARY_CONDITIONAL",
        SUBTYPE_ERROR: "BOUNDARY_ERROR",
        SUBTYPE_CANCEL: "BOUNDARY_CANCEL",
        SUBTYPE_COMPENSATION: "BOUNDARY_COMPENSATION",
        SUBTYPE_SIGNAL: "BOUNDARY_SIGNAL",
        SUBTYPE_MULTIPLE: "BOUNDARY_MULTIPLE",
        SUBTYPE_PARALLEL_MULTIPLE: "BOUNDARY_PARALLEL_MULTIPLE",
    },
    POSITION_END: {
        SUBTYPE_PLAIN: "END_EVENT",
        SUBTYPE_MESSAGE: "END_MESSAGE",
        SUBTYPE_ERROR: "END_ERROR",
        SUBTYPE_SIGNAL: "END_SIGNAL",
        SUBTYPE_TERMINATE: "END_TERMINATE",
        SUBTYPE_ESCALATION: "END_ESCALATION",
        SUBTYPE_COMPENSATION: "END_COMPENSATION",
        SUBTYPE_CANCEL: "END_CANCEL",
        SUBTYPE_MULTIPLE: "END_MULTIPLE",
    },
}

SUBTYPE_TITLES = {
    SUBTYPE_PLAIN: "Без подтипа",
    SUBTYPE_MESSAGE: "Сообщение",
    SUBTYPE_TIMER: "Таймер",
    SUBTYPE_CONDITIONAL: "Условие",
    SUBTYPE_SIGNAL: "Сигнал",
    SUBTYPE_ERROR: "Ошибка",
    SUBTYPE_ESCALATION: "Эскалация",
    SUBTYPE_COMPENSATION: "Компенсация",
    SUBTYPE_LINK: "Ссылка",
    SUBTYPE_TERMINATE: "Прерывание",
    SUBTYPE_CANCEL: "Отмена",
    SUBTYPE_MULTIPLE: "Несколько",
    SUBTYPE_PARALLEL_MULTIPLE: "Несколько параллельно",
}


@dataclass(frozen=True)
class EventVariant:
    """Один вариант события: положение, подтип и код символа из каталога."""

    position: str
    subtype: str
    kind: str

    @property
    def position_title(self) -> str:
        return POSITION_TITLES[self.position]

    @property
    def subtype_title(self) -> str:
        return SUBTYPE_TITLES[self.subtype]

    @property
    def title(self) -> str:
        """Короткое название для палитры: «Промежуточное: таймер»."""
        if self.subtype == SUBTYPE_PLAIN:
            return self.position_title
        return f"{self.position_title}: {self.subtype_title}"

    @property
    def label(self) -> str:
        """Подпись с пояснением из каталога, если символ там есть."""
        info = CATALOG.get(self.kind)
        if info:
            return info["label"]
        return self.title

    @property
    def available(self) -> bool:
        """Есть ли символ в каталоге (иначе вариант заявлен, но не нарисован)."""
        return self.kind in CATALOG


def variants_for_position(position: str) -> list[EventVariant]:
    """Все варианты одного положения в порядке объявления."""
    mapping = COMPATIBILITY.get(position, {})
    return [
        EventVariant(position=position, subtype=subtype, kind=kind)
        for subtype, kind in mapping.items()
    ]


def all_variants() -> list[EventVariant]:
    result: list[EventVariant] = []
    for position in POSITION_ORDER:
        result.extend(variants_for_position(position))
    return result


def variant_for(position: str, subtype: str) -> EventVariant | None:
    kind = COMPATIBILITY.get(position, {}).get(subtype)
    if kind is None:
        return None
    return EventVariant(position=position, subtype=subtype, kind=kind)


def position_of_kind(kind: str) -> str | None:
    """Обратный поиск: к какому положению относится код символа."""
    for position, mapping in COMPATIBILITY.items():
        if kind in mapping.values():
            return position
    return None


def subtype_of_kind(kind: str) -> str | None:
    for mapping in COMPATIBILITY.values():
        for subtype, candidate in mapping.items():
            if candidate == kind:
                return subtype
    return None


def boundary_kinds() -> list[str]:
    """Коды граничных событий — они крепятся к задаче, а не ставятся на поле."""
    return list(COMPATIBILITY[POSITION_BOUNDARY].values())


def is_boundary(kind: str) -> bool:
    return kind in boundary_kinds()


def missing_kinds() -> list[str]:
    """Варианты, для которых ещё нет символа в каталоге.

    Список должен быть пустым: он показывает, какие подтипы заявлены в
    таблице совместимости, но не нарисованы. Используется тестом, чтобы
    интерфейс не показывал пустые кнопки.
    """
    return sorted({v.kind for v in all_variants() if not v.available})


def catch_or_throw(position: str, subtype: str) -> str:
    """Поведение промежуточного события: «поймать» или «выбросить».

    Промежуточное событие может ждать событие (catch) либо сообщать о нём
    (throw). Ссылка и компенсация — только «выбросить», остальные в этой
    реализации трактуются как ожидание. Для начальных, граничных и
    конечных положение само задаёт поведение, поэтому возвращается
    пустая строка.
    """
    if position != POSITION_INTERMEDIATE:
        return ""
    if subtype in {SUBTYPE_LINK, SUBTYPE_COMPENSATION}:
        return "throw"
    if subtype in {SUBTYPE_PLAIN, SUBTYPE_ERROR, SUBTYPE_ESCALATION}:
        return "throw"
    return "catch"
