# RS_BPMN_FOUNDATION_V35
"""
Каталог основных элементов и потоков BPMN.

Модуль не хранит диаграммы и не объявляет редактор BPMN готовым.
Проверки ниже являются предварительными и не заменяют полную
валидацию BPMN 2.0.
"""
from __future__ import annotations

SYMBOLS = {
    "START_EVENT": {
        "name": "Начальное событие",
        "group": "EVENT",
        "shape": "circle",
    },
    "INTERMEDIATE_EVENT": {
        "name": "Промежуточное событие",
        "group": "EVENT",
        "shape": "double_circle",
    },
    "END_EVENT": {
        "name": "Конечное событие",
        "group": "EVENT",
        "shape": "bold_circle",
    },
    "TASK": {
        "name": "Задача",
        "group": "ACTIVITY",
        "shape": "rounded_rectangle",
    },
    "SUBPROCESS": {
        "name": "Подпроцесс",
        "group": "ACTIVITY",
        "shape": "rounded_rectangle_plus",
    },
    "EXCLUSIVE_GATEWAY": {
        "name": "Исключающий шлюз",
        "group": "GATEWAY",
        "shape": "diamond_x",
    },
    "PARALLEL_GATEWAY": {
        "name": "Параллельный шлюз",
        "group": "GATEWAY",
        "shape": "diamond_plus",
    },
    "INCLUSIVE_GATEWAY": {
        "name": "Включающий шлюз",
        "group": "GATEWAY",
        "shape": "diamond_circle",
    },
    "PARTICIPANT": {
        "name": "Участник / пул",
        "group": "CONTAINER",
        "shape": "pool",
    },
    "LANE": {
        "name": "Дорожка",
        "group": "CONTAINER",
        "shape": "lane",
    },
}

FLOWS = {
    "CONTROL": {
        "name": "Поток управления",
        "line": "solid",
        "start_marker": "none",
        "end_marker": "filled_arrow",
    },
    "CONDITIONAL": {
        "name": "Условный поток управления",
        "line": "solid",
        "start_marker": "conditional_diamond",
        "end_marker": "filled_arrow",
    },
    "DEFAULT": {
        "name": "Поток управления «в остальных случаях»",
        "line": "solid",
        "start_marker": "default_slash",
        "end_marker": "filled_arrow",
    },
    "MESSAGE": {
        "name": "Поток сообщений",
        "line": "dashed",
        "start_marker": "open_circle",
        "end_marker": "open_arrow",
    },
    "TECHNICAL": {
        "name": "Техническая связь репозитория",
        "line": "solid",
        "start_marker": "none",
        "end_marker": "filled_arrow",
    },
}

SEQUENCE_FLOWS = frozenset({"CONTROL", "CONDITIONAL", "DEFAULT"})
FLOW_NODES = frozenset({
    "START_EVENT",
    "INTERMEDIATE_EVENT",
    "END_EVENT",
    "TASK",
    "SUBPROCESS",
    "EXCLUSIVE_GATEWAY",
    "PARALLEL_GATEWAY",
    "INCLUSIVE_GATEWAY",
})

# Эти типы потенциально могут участвовать в обмене сообщениями.
# Окончательная проверка зависит от участников и свойств элемента.
MESSAGE_CANDIDATES = frozenset({
    "PARTICIPANT",
    "TASK",
    "SUBPROCESS",
    "START_EVENT",
    "INTERMEDIATE_EVENT",
    "END_EVENT",
})


def check_connection(flow_type, source_type, target_type):
    """
    Предварительная проверка связи.

    Возвращает словарь:
        allowed: False — заведомо недопустимо;
                 True — базовые ограничения соблюдены.
        requires_context: требуется дополнительная проверка
                          участника, направления события и т. п.
        message: пояснение.

    Эта функция не создаёт и не изменяет связи.
    """
    if flow_type not in FLOWS:
        return {
            "allowed": False,
            "requires_context": False,
            "message": "Неизвестный тип потока.",
        }

    if source_type not in SYMBOLS or target_type not in SYMBOLS:
        return {
            "allowed": False,
            "requires_context": False,
            "message": "Неизвестный тип символа.",
        }

    if flow_type == "TECHNICAL":
        return {
            "allowed": True,
            "requires_context": True,
            "message": (
                "Техническая связь определяется репозиторием, "
                "а не правилами BPMN."
            ),
        }

    if flow_type in SEQUENCE_FLOWS:
        if source_type not in FLOW_NODES or target_type not in FLOW_NODES:
            return {
                "allowed": False,
                "requires_context": False,
                "message": (
                    "Поток управления соединяет элементы процесса, "
                    "а не пул или дорожку."
                ),
            }

        if source_type == "END_EVENT":
            return {
                "allowed": False,
                "requires_context": False,
                "message": "Из конечного события поток не выходит.",
            }

        if target_type == "START_EVENT":
            return {
                "allowed": False,
                "requires_context": False,
                "message": "В начальное событие поток не входит.",
            }

        if (
            flow_type == "DEFAULT"
            and SYMBOLS[source_type]["group"] not in {"ACTIVITY", "GATEWAY"}
        ):
            return {
                "allowed": False,
                "requires_context": False,
                "message": (
                    "Поток по умолчанию должен исходить "
                    "из действия или шлюза."
                ),
            }

        return {
            "allowed": True,
            "requires_context": True,
            "message": (
                "Требуется дополнительная проверка процесса, "
                "типа шлюза и свойств потока."
            ),
        }

    if flow_type == "MESSAGE":
        if (
            source_type not in MESSAGE_CANDIDATES
            or target_type not in MESSAGE_CANDIDATES
        ):
            return {
                "allowed": False,
                "requires_context": False,
                "message": (
                    "Выбранный тип символа не поддерживает "
                    "обмен сообщениями."
                ),
            }

        return {
            "allowed": True,
            "requires_context": True,
            "message": (
                "Нужно проверить, что элементы принадлежат "
                "разным участникам и поддерживают обмен сообщениями."
            ),
        }

    return {
        "allowed": False,
        "requires_context": False,
        "message": "Для этого типа потока нет правила.",
    }


def self_test():
    assert len(SYMBOLS) >= 10
    assert set(FLOWS) == {
        "CONTROL", "CONDITIONAL", "DEFAULT", "MESSAGE", "TECHNICAL"
    }
    assert not check_connection(
        "CONTROL", "END_EVENT", "TASK"
    )["allowed"]
    assert not check_connection(
        "CONTROL", "TASK", "START_EVENT"
    )["allowed"]
    assert not check_connection(
        "CONTROL", "PARTICIPANT", "TASK"
    )["allowed"]
    assert check_connection(
        "CONTROL", "TASK", "END_EVENT"
    )["allowed"]
    message = check_connection("MESSAGE", "TASK", "PARTICIPANT")
    assert message["allowed"] and message["requires_context"]
    assert not check_connection(
        "MESSAGE", "EXCLUSIVE_GATEWAY", "TASK"
    )["allowed"]
    assert not check_connection(
        "UNKNOWN", "TASK", "TASK"
    )["allowed"]
