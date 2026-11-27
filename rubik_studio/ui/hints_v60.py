# RS_HINT_SYSTEM_V60
"""Единая система подсказок: «i», «?», «!».

Пользователь просил значки, по которым сразу понятно, что перед ним:

* **«i» в полом круге с чёрным контуром** — просто информация. Навёл
  курсор — всплыло пояснение.
* **«?» в жёлтом треугольнике** — возможная ошибка, сомнительное место.
  Понадобится и в других задачах, поэтому это отдельный вид.
* **«!» в красном круге** — ошибка, неисправность или нарушение: что
  случилось и почему появилось. Этот же значок используется, чтобы
  показывать пользователю найденные проблемы и подсказывать, где искать
  причину.

Раньше подсказки были разбросаны по коду: где-то серый текст мелким
шрифтом, где-то `ui.tooltip`, часть надписей устарела. Теперь есть один
модуль, один внешний вид и одно поведение.

Правила, которые соблюдает модуль:

1. Значок всегда одного вида, независимо от темы. Цвета фиксированные:
   так «!» не потеряется на тёмном фоне.
2. Подсказка открывается наведением и по клику, поэтому работает и на
   сенсорном экране.
3. Текст подсказки — это данные, а не разметка: он попадает в атрибут
   как обычная строка, без разбора и без HTML.
4. У каждой подсказки есть «место» (ключ), чтобы один и тот же текст
   не дублировался в разных файлах.
"""

from __future__ import annotations

from collections.abc import Iterable

from nicegui import ui

# Виды значков.
KIND_INFO = "info"
KIND_WARNING = "warning"
KIND_ERROR = "error"

# Порядок — по возрастанию важности: используется при сортировке отчёта.
SEVERITY_ORDER = {KIND_INFO: 0, KIND_WARNING: 1, KIND_ERROR: 2}

KIND_TITLES = {
    KIND_INFO: "Информация",
    KIND_WARNING: "Возможная ошибка",
    KIND_ERROR: "Ошибка",
}

# Внешний вид: фон, цвет контура и текста, фигура.
STYLES = {
    KIND_INFO: {
        "background": "transparent",
        "border": "1.5px solid #1F2937",
        "color": "#1F2937",
        "radius": "50%",
        "glyph": "i",
    },
    KIND_WARNING: {
        "background": "#F5C518",
        "border": "1.5px solid #B45309",
        "color": "#1F2937",
        "radius": "3px",
        "glyph": "?",
    },
    KIND_ERROR: {
        "background": "#DC2626",
        "border": "1.5px solid #7F1D1D",
        "color": "#FFFFFF",
        "radius": "50%",
        "glyph": "!",
    },
}

# Треугольник для «?»: поворачиваем квадрат на 45 градусов было бы
# приблизительно, поэтому рисуем настоящий треугольник через clip-path.
WARNING_SHAPE = "polygon(50% 0%, 100% 100%, 0% 100%)"


def _style_css(kind: str, size: int) -> str:
    style = STYLES[kind]
    css = (
        f"width:{size}px; height:{size}px; flex:none; "
        f"display:inline-flex; align-items:center; justify-content:center; "
        f"font-size:{max(9, round(size * 0.62))}px; font-weight:700; "
        f"line-height:1; cursor:help; user-select:none; "
        f"color:{style['color']}; background:{style['background']}; "
        f"border:{style['border']}; box-sizing:border-box; "
    )

    if kind == KIND_WARNING:
        # Треугольник: текст смещаем к основанию, иначе он висит на
        # вершине и читается плохо.
        css += (
            f"clip-path:{WARNING_SHAPE}; padding-top:{round(size * 0.30)}px; "
            "border:none; "
        )
    else:
        css += f"border-radius:{style['radius']}; "

    return css


def hint_icon(
    text: str,
    kind: str = KIND_INFO,
    *,
    size: int = 18,
    title: str = "",
    mark: str = "",
) -> ui.element:
    """Значок подсказки. Текст показывается по наведению и по клику.

    ``kind`` — один из KIND_INFO, KIND_WARNING, KIND_ERROR.
    ``mark`` — метка для автотестов.
    """
    if kind not in STYLES:
        raise ValueError(f"Неизвестный вид подсказки: {kind}")

    caption = title or KIND_TITLES[kind]
    glyph = STYLES[kind]["glyph"]

    box = ui.element("div").style(_style_css(kind, size))

    # RS_HINT_PROPS_V60
    # Текст подсказки нельзя передавать через .props(): NiceGUI разбирает
    # строку свойств через ast.literal_eval, и обратный слэш в тексте
    # (например, путь Windows «C:\Users\...») ломал разбор с
    # SyntaxError. Поэтому атрибуты ставим напрямую в словарь свойств —
    # там значение остаётся обычной строкой без разбора.
    box.props(f'data-rs-hint="{kind}"')
    box._props["tabindex"] = "0"
    box._props["role"] = "img"
    box._props["aria-label"] = f"{caption}: {text}"
    box.mark(mark or f"rs-hint-icon-{kind}")

    with box:
        ui.html(glyph, sanitize=False).style("pointer-events:none;")

    # Всплывающее окно: свой размер и перенос строк, потому что
    # стандартный tooltip обрезает длинный текст.
    with box:
        with ui.menu().props("auto-close=false").style(
            "max-width:340px; padding:10px 12px;"
        ) as menu:
            with ui.column().classes("gap-1"):
                ui.label(caption).style(
                    "font-size:12px; font-weight:700; color:#111827;"
                )
                ui.label(str(text)).style(
                    "font-size:12px; line-height:17px; color:#1F2937; "
                    "white-space:normal;"
                )

    box.on("mouseenter", lambda _e: menu.open())
    box.on("mouseleave", lambda _e: menu.close())
    box.on("click", lambda _e: menu.toggle())
    box.on("focus", lambda _e: menu.open())
    box.on("blur", lambda _e: menu.close())

    return box


def info_badge(text: str, *, size: int = 18, mark: str = "") -> ui.element:
    """«i» в полом круге — короткое пояснение рядом с надписью."""
    return hint_icon(text, KIND_INFO, size=size, mark=mark)


def warning_badge(text: str, *, size: int = 18, mark: str = "") -> ui.element:
    """«?» в жёлтом треугольнике — возможная ошибка."""
    return hint_icon(text, KIND_WARNING, size=size, mark=mark)


def error_badge(text: str, *, size: int = 18, mark: str = "") -> ui.element:
    """«!» в красном круге — ошибка: что случилось и почему."""
    return hint_icon(text, KIND_ERROR, size=size, mark=mark)


def hint_label(text: str, kind: str = KIND_INFO, *, mark: str = "") -> None:
    """Строка «значок + текст» — вместо мелкого серого абзаца."""
    with ui.row().classes("items-center gap-2 no-wrap"):
        hint_icon(text, kind, mark=mark)
        ui.label(str(text)).classes("text-sm").style(
            "line-height:18px; white-space:normal;"
        )


# ── Диагностика: ошибки для пользователя ───────────────────────────────────

def problem(
    kind: str,
    title: str,
    reason: str = "",
    where: str = "",
) -> dict:
    """Описание проблемы: что случилось, почему и где искать.

    Формат один для всех мест, поэтому отчёт о проверке и подсказки в
    интерфейсе выглядят одинаково.
    """
    return {
        "kind": kind,
        "title": str(title),
        "reason": str(reason),
        "where": str(where),
        "severity": SEVERITY_ORDER.get(kind, 0),
    }


def sort_problems(items: Iterable[dict]) -> list[dict]:
    """Сначала ошибки, потом предупреждения, потом информация."""
    return sorted(items, key=lambda item: -item.get("severity", 0))


def problem_text(item: dict) -> str:
    """Текст проблемы одной строкой — для журнала и подсказки."""
    parts = [item.get("title", "")]
    if item.get("reason"):
        parts.append("Причина: " + item["reason"])
    if item.get("where"):
        parts.append("Где: " + item["where"])
    return ". ".join(part for part in parts if part)


def render_problem(item: dict, *, mark: str = "") -> None:
    """Показать проблему строкой: значок, заголовок, причина, место."""
    with ui.column().classes("w-full gap-1"):
        with ui.row().classes("items-center gap-2 no-wrap"):
            hint_icon(
                problem_text(item),
                item.get("kind", KIND_INFO),
                mark=mark or "rs-problem-icon",
            )
            ui.label(item.get("title", "")).classes("text-sm font-semibold")

        if item.get("reason"):
            ui.label("Причина: " + item["reason"]).classes(
                "text-xs rs-muted"
            )
        if item.get("where"):
            ui.label("Где: " + item["where"]).classes("text-xs rs-muted")
