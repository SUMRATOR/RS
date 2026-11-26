# RS_BPMN_SHAPES_V55
"""Отрисовка символов BPMN для поля, палитры и колеса V.

Один источник разметки: символ выглядит одинаково в палитре, на схеме
и в радиальном колесе. Модуль не импортирует NiceGUI — возвращает строки
SVG/HTML, поэтому его можно проверить автотестом без браузера.

Требования аудитории (студенты и преподаватели):
  * крупный контур, двойной контур для конечных событий;
  * внутри события — узнаваемая пиктограмма, а не только цвет;
  * подпись под символом читаемым кеглем;
  * никакой зависимости от знания нотации для базовых символов.
"""

from __future__ import annotations

import html

from rubik_studio.core.bpmn_catalog_v55 import CATALOG

# ── Палитра (тёмная тема, контраст ≥ 4.5:1 на фоне #17202c) ─────────────────
COLOR = {
    "canvas": "#17202c",
    "panel": "#1E2B45",
    "text": "#E8EDF5",
    "muted": "#A9B8CF",
    "start": "#4ED6A0",
    "end": "#FF8A8A",
    "mid": "#FFC857",
    "task": "#7FB2FF",
    "subprocess": "#A99BFF",
    "gateway": "#FFC857",
    "data": "#BFD4EE",
    "lane": "#8FA3BF",
}

# Базовый размер полотна символа. Поле масштабирует его через viewBox.
VIEW_W = 180
VIEW_H = 70
EVENT_R = 30
GATEWAY_R = 30

# Пиктограммы внутри событий: простые фигуры, узнаваемые без терминов.
_PICTO = {
    "message": (
        '<rect x="-13" y="-9" width="26" height="18" rx="2" fill="none" '
        'stroke="{c}" stroke-width="2"/>'
        '<path d="M-13 -8 L0 2 L13 -8" fill="none" stroke="{c}" stroke-width="2"/>'
    ),
    "timer": (
        '<circle cx="0" cy="0" r="12" fill="none" stroke="{c}" stroke-width="2"/>'
        '<path d="M0 -7 V0 L6 4" fill="none" stroke="{c}" stroke-width="2" '
        'stroke-linecap="round"/>'
    ),
    "condition": (
        '<rect x="-12" y="-12" width="24" height="24" rx="2" fill="none" '
        'stroke="{c}" stroke-width="2"/>'
        '<path d="M-6 -6 L6 6 M6 -6 L-6 6" fill="none" stroke="{c}" stroke-width="2"/>'
    ),
    "signal": (
        '<path d="M-13 -7 L0 -13 L13 -7 L0 13 Z" fill="none" stroke="{c}" '
        'stroke-width="2"/>'
    ),
    "error": (
        '<path d="M-6 -12 L6 -1 L1 -1 L8 12 L-4 1 L1 1 Z" fill="{c}"/>'
    ),
    "escalation": (
        '<path d="M0 -13 L13 9 L-13 9 Z" fill="none" stroke="{c}" stroke-width="2"/>'
        '<path d="M0 -5 V3" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<circle cx="0" cy="7" r="1.6" fill="{c}"/>'
    ),
    "link": (
        '<path d="M-10 -6 L6 -6 L6 -12 L14 0 L6 12 L6 6 L-10 6 Z" fill="{c}"/>'
    ),
    "compensation": (
        '<path d="M-9 -9 L9 -9 L9 9 L-9 9 Z" fill="none" stroke="{c}" stroke-width="2"/>'
        '<path d="M-4 9 L-4 15 L4 15 M-4 15 L-13 15" fill="none" stroke="{c}" '
        'stroke-width="2"/>'
    ),
    "terminate": '<circle cx="0" cy="0" r="13" fill="{c}"/>',
    "multi": (
        '<path d="M0 -13 L3 -4 L13 -4 L5 2 L8 11 L0 6 L-8 11 L-5 2 L-13 -4 '
        'L-3 -4 Z" fill="none" stroke="{c}" stroke-width="1.8"/>'
    ),
}

# Событие → (тип контура, пиктограмма).
#   thin  — начальное, thick — конечное (двойная линия), mid — промежуточное.
_EVENT_SPEC = {
    "START_EVENT": ("thin", None),
    "START_MESSAGE": ("thin", "message"),
    "START_TIMER": ("thin", "timer"),
    "START_CONDITIONAL": ("thin", "condition"),
    "START_SIGNAL": ("thin", "signal"),
    "START_ERROR": ("thin", "error"),
    "INTERMEDIATE_EVENT": ("mid", None),
    "INTERMEDIATE_MESSAGE": ("mid", "message"),
    "INTERMEDIATE_TIMER": ("mid", "timer"),
    "INTERMEDIATE_ESCALATION": ("mid", "escalation"),
    "INTERMEDIATE_CONDITIONAL": ("mid", "condition"),
    "INTERMEDIATE_LINK": ("mid", "link"),
    "INTERMEDIATE_SIGNAL": ("mid", "signal"),
    "INTERMEDIATE_ERROR": ("mid", "error"),
    "INTERMEDIATE_COMPENSATION": ("mid", "compensation"),
    "END_EVENT": ("thick", None),
    "END_TERMINATE": ("thick", "terminate"),
    "END_MESSAGE": ("thick", "message"),
    "END_ERROR": ("thick", "error"),
    "END_SIGNAL": ("thick", "signal"),
}

# Шлюз → маркер внутри ромба.
_GATEWAY_MARK = {
    "EXCLUSIVE_GATEWAY": (
        '<path d="M-9 -9 L9 9 M9 -9 L-9 9" fill="none" stroke="{c}" '
        'stroke-width="3.2" stroke-linecap="round"/>'
    ),
    "PARALLEL_GATEWAY": (
        '<path d="M0 -11 V11 M-11 0 H11" fill="none" stroke="{c}" '
        'stroke-width="3.2" stroke-linecap="round"/>'
    ),
    "INCLUSIVE_GATEWAY": (
        '<circle cx="0" cy="0" r="10" fill="none" stroke="{c}" stroke-width="3"/>'
    ),
    "EVENT_BASED_GATEWAY": (
        '<circle cx="0" cy="0" r="10" fill="none" stroke="{c}" stroke-width="2.4"/>'
        '<circle cx="0" cy="0" r="6" fill="none" stroke="{c}" stroke-width="2.4"/>'
    ),
    "COMPLEX_GATEWAY": (
        '<path d="M0 -11 V11 M-9.5 -5.5 L9.5 5.5 M9.5 -5.5 L-9.5 5.5" fill="none" '
        'stroke="{c}" stroke-width="2.8" stroke-linecap="round"/>'
    ),
    "EXCLUSIVE_EVENT_GATEWAY": (
        '<path d="M0 -11 L9.5 -4 L6 10 L-6 10 L-9.5 -4 Z" fill="none" '
        'stroke="{c}" stroke-width="2.4"/>'
        '<circle cx="0" cy="0" r="4.5" fill="none" stroke="{c}" stroke-width="2"/>'
    ),
    "PARALLEL_EVENT_GATEWAY": (
        '<path d="M0 -9 V9 M-9 0 H9" fill="none" stroke="{c}" stroke-width="2.6"/>'
        '<circle cx="0" cy="0" r="11" fill="none" stroke="{c}" stroke-width="2.4"/>'
    ),
}

# Задача → пиктограмма в левом верхнем углу.
_TASK_PICTO = {
    "USER_TASK": (
        '<circle cx="0" cy="-4" r="4" fill="none" stroke="{c}" stroke-width="1.8"/>'
        '<path d="M-7 8 C-7 0 7 0 7 8" fill="none" stroke="{c}" stroke-width="1.8"/>'
    ),
    "SERVICE_TASK": (
        '<circle cx="0" cy="0" r="6" fill="none" stroke="{c}" stroke-width="1.8"/>'
        '<path d="M0 -10 V-7 M0 7 V10 M-10 0 H-7 M7 0 H10" stroke="{c}" '
        'stroke-width="1.8"/>'
    ),
    "MANUAL_TASK": (
        '<path d="M-7 7 L-3 -3 L7 -7 L3 3 Z" fill="none" stroke="{c}" '
        'stroke-width="1.8"/>'
    ),
    "SCRIPT_TASK": (
        '<path d="M-7 -7 H7 M-7 0 H7 M-7 7 H7" stroke="{c}" stroke-width="1.8"/>'
    ),
    "SEND_TASK": (
        '<path d="M-8 -6 L8 0 L-8 6 L-5 0 Z" fill="{c}"/>'
    ),
    "RECEIVE_TASK": (
        '<rect x="-8" y="-6" width="16" height="12" rx="2" fill="none" '
        'stroke="{c}" stroke-width="1.8"/>'
        '<path d="M-8 -5 L0 1 L8 -5" fill="none" stroke="{c}" stroke-width="1.8"/>'
    ),
    "BUSINESS_RULE_TASK": (
        '<rect x="-8" y="-8" width="16" height="16" fill="none" stroke="{c}" '
        'stroke-width="1.8"/>'
        '<path d="M-4 -8 V8" stroke="{c}" stroke-width="1.8"/>'
    ),
}


def _event_svg(kind: str) -> str:
    contour, picto = _EVENT_SPEC[kind]
    stroke = {"thin": 2.4, "mid": 2.4, "thick": 5.5}[contour]
    color = {"thin": COLOR["start"], "mid": COLOR["mid"], "thick": COLOR["end"]}[contour]

    body = (
        f'<circle cx="0" cy="0" r="{EVENT_R}" fill="{COLOR["panel"]}" '
        f'stroke="{color}" stroke-width="{stroke}"/>'
    )

    if contour == "mid":
        # Внутренний тонкий контур — признак промежуточного события.
        body += (
            f'<circle cx="0" cy="0" r="{EVENT_R - 4}" fill="none" '
            f'stroke="{color}" stroke-width="1.6" opacity="0.85"/>'
        )

    if picto:
        glyph = _PICTO[picto].format(c=COLOR["text"])
        body += f'<g transform="translate(0,-1) scale(0.82)">{glyph}</g>'

    return body


def _gateway_svg(kind: str) -> str:
    mark = _GATEWAY_MARK[kind].format(c=COLOR["text"])
    return (
        f'<polygon points="0,{-GATEWAY_R} {GATEWAY_R},0 0,{GATEWAY_R} '
        f'{-GATEWAY_R},0" fill="{COLOR["panel"]}" stroke="{COLOR["gateway"]}" '
        f'stroke-width="2.6"/>{mark}'
    )


def _task_svg(kind: str, width: int) -> str:
    subprocess = kind == "SUBPROCESS"
    stroke = COLOR["subprocess"] if subprocess else COLOR["task"]
    height = 46
    x = -width / 2
    y = -height / 2
    body = (
        f'<rect x="{x:.0f}" y="{y:.0f}" width="{width}" height="{height}" rx="8" '
        f'fill="{COLOR["panel"]}" stroke="{stroke}" stroke-width="2.4"/>'
    )
    if subprocess:
        body += (
            f'<rect x="-8" y="{y + height - 16:.0f}" width="16" height="12" '
            f'fill="none" stroke="{COLOR["subprocess"]}" stroke-width="1.6"/>'
            f'<path d="M0 {y + height - 14:.0f} V{y + height - 6:.0f} '
            f'M-5 {y + height - 10:.0f} H5" stroke="{COLOR["subprocess"]}" '
            f'stroke-width="1.6"/>'
        )
    elif kind in _TASK_PICTO:
        glyph = _TASK_PICTO[kind].format(c=COLOR["text"])
        body += f'<g transform="translate({x + 18:.0f},{y + 16:.0f})">{glyph}</g>'
    return body


def _data_svg(kind: str) -> str:
    body = (
        f'<path d="M-26 -26 H16 L26 -16 V26 H-26 Z" fill="{COLOR["panel"]}" '
        f'stroke="{COLOR["data"]}" stroke-width="2"/>'
        f'<path d="M16 -26 V-16 H26" fill="none" stroke="{COLOR["data"]}" '
        f'stroke-width="1.6"/>'
    )
    if kind == "DATA_INPUT":
        body += (
            f'<path d="M-18 4 H8 M2 -2 L8 4 L2 10" fill="none" '
            f'stroke="{COLOR["text"]}" stroke-width="2.4" stroke-linecap="round"/>'
        )
    elif kind == "DATA_OUTPUT":
        body += (
            f'<path d="M16 4 H-10 M-4 -2 L-10 4 L-4 10" fill="none" '
            f'stroke="{COLOR["text"]}" stroke-width="2.4" stroke-linecap="round"/>'
        )
    elif kind == "DATA_COLLECTION":
        body += (
            f'<path d="M-8 18 V24 M0 18 V24 M8 18 V24" stroke="{COLOR["text"]}" '
            f'stroke-width="2.4"/>'
        )
    elif kind == "DATA_STORE":
        body = (
            f'<rect x="-26" y="-14" width="52" height="28" rx="4" fill="{COLOR["panel"]}" '
            f'stroke="{COLOR["data"]}" stroke-width="2"/>'
            f'<path d="M-26 -4 H26" stroke="{COLOR["data"]}" stroke-width="1.6"/>'
            f'<path d="M-10 -14 V14" stroke="{COLOR["data"]}" stroke-width="1.6"/>'
        )
    return body


def _container_svg(kind: str, width: int, height: int) -> str:
    if kind == "PARTICIPANT":
        return (
            f'<rect x="0" y="0" width="{width}" height="{height}" '
            f'fill="{COLOR["panel"]}" stroke="{COLOR["task"]}" stroke-width="2.4"/>'
            f'<path d="M34 0 V{height}" stroke="{COLOR["task"]}" stroke-width="2.4"/>'
        )
    return (
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="none" '
        f'stroke="{COLOR["lane"]}" stroke-width="2.4"/>'
        f'<path d="M32 0 V{height}" stroke="{COLOR["lane"]}" stroke-width="2"/>'
    )


def svg_inner(kind: str, width: int = 180, height: int = 70) -> str:
    """Внутренности SVG без обёртки <svg>: одна геометрия для всех мест."""
    if kind in _EVENT_SPEC:
        return _event_svg(kind)
    if kind in _GATEWAY_MARK:
        return _gateway_svg(kind)
    if kind in {"PARTICIPANT", "LANE"}:
        return _container_svg(kind, width, height)
    if kind in {"DATA_STORE", "DATA_OBJECT"} or kind.startswith("DATA_"):
        return _data_svg(kind)
    return _task_svg(kind, width=max(120, width - 60))


def shape_markup(kind: str, name: str = "", width: int = 180, height: int = 70) -> str:
    """Готовая разметка символа: SVG + подпись под ним.

    Используется на поле диаграммы. Подпись экранируется.
    """
    title = html.escape(str(name or ""), quote=True)
    inner = svg_inner(kind, width, height)

    is_container = kind in {"PARTICIPANT", "LANE"}
    is_event = kind in _EVENT_SPEC
    is_gateway = kind in _GATEWAY_MARK

    if is_container:
        label = (
            f'<div style="position:absolute;left:40px;top:6px;right:8px;'
            f'font-size:13px;line-height:16px;color:{COLOR["text"]};'
            f'overflow:hidden;max-height:52px;overflow-wrap:anywhere;'
            f'pointer-events:none;">{title}</div>'
        )
        return (
            f'<div style="position:relative;width:{width}px;height:{height}px;'
            f'pointer-events:none;">'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" '
            f'style="display:block;pointer-events:none;">{inner}</svg>'
            f'{label}</div>'
        )

    # События и шлюзы занимают центр полотна, подпись — под фигурой.
    offset_y = height / 2 - 2
    if is_event or is_gateway:
        figure = (
            f'<g transform="translate({width / 2:.0f},{offset_y:.0f})">{inner}</g>'
        )
        caption_top = height / 2 + 26
    else:
        figure = (
            f'<g transform="translate({width / 2:.0f},{offset_y:.0f})">{inner}</g>'
        )
        caption_top = height / 2 + 4

    label = (
        f'<div style="position:absolute;left:0;top:{caption_top:.0f}px;width:{width}px;'
        f'text-align:center;font-size:13px;line-height:17px;color:{COLOR["text"]};'
        f'overflow-wrap:anywhere;pointer-events:none;">{title}</div>'
    )

    return (
        f'<div style="position:relative;width:{width}px;height:{height}px;'
        f'pointer-events:none;">'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="display:block;pointer-events:none;">'
        f'{figure}</svg>{label}</div>'
    )


def thumbnail_svg(kind: str, size: int = 44) -> str:
    """Миниатюра для палитры и колеса: только фигура, без подписи."""
    inner = svg_inner(kind, width=120, height=44)
    if kind in _EVENT_SPEC or kind in _GATEWAY_MARK:
        scale = size / (EVENT_R * 2.6)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="{-size / 2 / scale:.1f} {-size / 2 / scale:.1f} '
            f'{size / scale:.1f} {size / scale:.1f}" aria-hidden="true">'
            f'{inner}</svg>'
        )
    if kind in {"PARTICIPANT", "LANE"}:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 120 44" aria-hidden="true">'
            f'{_container_svg(kind, 118, 42)}</svg>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size * 0.55:.0f}" '
        f'viewBox="-70 -26 140 52" aria-hidden="true">{inner}</svg>'
    )


def palette_groups() -> list[tuple[str, list[tuple[str, str, str, str]]]]:
    """Группы палитры: (группа, [(код, подпись, подсказка, миниатюра)])."""
    from rubik_studio.core.bpmn_catalog_v55 import by_groups

    result = []
    for group, items in by_groups():
        result.append(
            (
                group,
                [
                    (kind, CATALOG[kind]["label"], CATALOG[kind]["hint"], thumbnail_svg(kind))
                    for kind, _label in items
                ],
            )
        )
    return result
