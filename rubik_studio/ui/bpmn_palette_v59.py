# RS_BPMN_PALETTE_COLLAPSE_V59
"""Сворачиваемые группы палитры и перетаскивание символа на поле.

Пользователь просил два изменения в панели символов редактора:

1. **Группы должны сворачиваться.** Сорок событий подряд заставляют
   прокручивать панель, чтобы добраться до задач и шлюзов.
2. **Символ нужно перетаскивать мышью на поле**, а не только добавлять
   кнопкой «+»: так проще сразу поставить его в нужное место.

Модуль не знает про состояние диаграммы: он рисует элементы и вызывает
переданные функции. Так его можно проверить без запуска редактора.
"""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

# Скрипт перетаскивания. Вынесен отдельно, чтобы его можно было проверить
# тестом и не собирать строку внутри отрисовки.
DRAG_SCRIPT = """
(() => {
    const canvasId = 'CANVAS_ID';

    // Приёмная сторона: поле диаграммы слушает это событие.
    function canvas() {
        return document.getElementById(canvasId);
    }

    window.__rsPaletteDragV59 ||= { armed: null };

    const state = window.__rsPaletteDragV59;

    function clearGhost() {
        if (state.ghost && state.ghost.parentElement) {
            state.ghost.remove();
        }
        state.ghost = null;
    }

    document.querySelectorAll('[data-rs-drag-symbol]').forEach(box => {
        if (box.dataset.rsDragReady === '1') return;
        box.dataset.rsDragReady = '1';

        box.addEventListener('pointerdown', event => {
            if (event.button !== 0) return;
            const kind = box.dataset.rsDragSymbol;
            if (!kind) return;

            event.preventDefault();
            state.armed = kind;

            // Полупрозрачная копия символа едет за курсором.
            const ghost = box.cloneNode(true);
            ghost.style.position = 'fixed';
            ghost.style.pointerEvents = 'none';
            ghost.style.opacity = '0.85';
            ghost.style.zIndex = '9999';
            ghost.style.transform = 'translate(-50%, -50%)';
            ghost.style.left = event.clientX + 'px';
            ghost.style.top = event.clientY + 'px';
            document.body.appendChild(ghost);
            state.ghost = ghost;

            function move(moveEvent) {
                if (!state.ghost) return;
                state.ghost.style.left = moveEvent.clientX + 'px';
                state.ghost.style.top = moveEvent.clientY + 'px';
            }

            function finish(upEvent) {
                document.removeEventListener('pointermove', move, true);
                document.removeEventListener('pointerup', finish, true);

                const target = canvas();
                const rect = target ? target.getBoundingClientRect() : null;
                const inside = rect &&
                    upEvent.clientX >= rect.left &&
                    upEvent.clientX <= rect.right &&
                    upEvent.clientY >= rect.top &&
                    upEvent.clientY <= rect.bottom;

                clearGhost();

                if (inside) {
                    // Переводим экранные координаты в координаты листа:
                    // учитываем и панорамирование, и масштаб.
                    const scale = parseFloat(target.dataset.rsViewScale || '1') || 1;
                    const transform = target.style.transform || '';
                    const match = transform.match(
                        /translate\\((-?[\\d.]+)px,\\s*(-?[\\d.]+)px\\)/
                    );
                    const panX = match ? parseFloat(match[1]) : 0;
                    const panY = match ? parseFloat(match[2]) : 0;

                    const worldX = (upEvent.clientX - rect.left - panX) / scale;
                    const worldY = (upEvent.clientY - rect.top - panY) / scale;

                    target.dispatchEvent(new CustomEvent(
                        'rs-palette-drop-v59',
                        {
                            detail: {
                                kind: kind,
                                x: worldX,
                                y: worldY
                            },
                            bubbles: true
                        }
                    ));
                }

                state.armed = null;
            }

            document.addEventListener('pointermove', move, true);
            document.addEventListener('pointerup', finish, true);
        });
    });
})();
"""


def collapse_group(
    title: str,
    count: int,
    render_items: Callable[[], None],
    *,
    start_open: bool = False,
    subtitle: str = "",
    key: str = "",
) -> ui.element:
    """Свернуть группу палитры в строку-заголовок.

    ``render_items`` вызывается только при раскрытии: свёрнутая группа не
    создаёт десятки элементов, поэтому панель открывается быстро.
    """
    box = ui.column().classes("w-full gap-1")

    with box:
        header = ui.row().classes(
            "w-full items-center gap-2 cursor-pointer select-none"
        )
        header.style(
            "padding:6px 8px; border-radius:8px; "
            "background:#1E2B45; border:1px solid #33415C;"
        )
        with header:
            arrow = ui.icon("chevron_right").style("font-size:16px; color:#A9B8CF;")
            ui.label(title).style(
                "font-size:12px; font-weight:700; letter-spacing:.04em; "
                "text-transform:uppercase; color:#E8EDF5; flex:1;"
            )
            ui.label(str(count)).style(
                "font-size:11px; color:#A9B8CF; background:#17202C; "
                "border-radius:8px; padding:0 6px;"
            )

        body = ui.column().classes("w-full gap-1")
        body.style("padding:2px 2px 4px 2px;")

        if subtitle:
            ui.label(subtitle).style("font-size:11px; color:#A9B8CF; line-height:14px;")

        is_open = {"value": start_open}

        def render_body() -> None:
            body.clear()
            if not is_open["value"]:
                return
            with body:
                render_items()

        def toggle() -> None:
            is_open["value"] = not is_open["value"]
            arrow.props(
                f"name={'expand_more' if is_open['value'] else 'chevron_right'}"
            )
            render_body()

        slug = key or title
        header.on("click", lambda _e: toggle())
        header.props(f'data-rs-group-toggle="{slug}"')
        header.mark(f"rs-group-{slug}")

        if start_open:
            render_body()

    return box


def draggable_symbol(
    kind: str,
    markup: str,
    caption: str,
    on_add: Callable[[str], None],
    on_hint: Callable[[str], None] | None = None,
    size: int = 44,
) -> None:
    """Карточка символа: перетаскивается на поле, добавляется кнопкой «+».

    Перетаскивание работает и мышью, и пальцем (pointer events). Кнопка
    «+» остаётся: ею пользуются, когда нужно поставить символ в свободное
    место автоматически.
    """
    with ui.element("div").style(
        "display:flex; flex-direction:column; align-items:center; gap:2px; "
        "padding:6px 4px; border-radius:10px; background:#1E2B45; "
        "border:1px solid #33415C; cursor:grab; touch-action:none;"
    ).props(f'data-rs-drag-symbol="{kind}" title="Перетащите на поле"') as card:
        card.mark(f"rs-drag-{kind}")
        # Текст метки на карточке: по нему проверяем, что символ виден.
        card.props(f'aria-label="{caption}" data-rs-symbol-label="{kind}"')

        ui.html(markup, sanitize=False).style(
            f"height:{size}px; display:flex; align-items:center; pointer-events:none;"
        )

        ui.label(caption).style(
            "font-size:11px; line-height:13px; text-align:center; "
            "color:#E8EDF5; pointer-events:none;"
        )

        with ui.row().classes("gap-1 no-wrap"):
            add = ui.button(
                icon="add",
                on_click=lambda _e, k=kind: on_add(k),
            ).props(
                "flat dense round size=sm "
                f'aria-label="Добавить: {kind}" data-rs-symbol-add={kind}'
            ).style("color:#7FB2FF;")
            # Прежние маркеры V55 сохранены: по ним ищут символ тесты и
            # программы чтения с экрана.
            add.mark(f"rs-add-{kind}")
            add.tooltip("Добавить на схему")

            if on_hint is not None:
                hint = ui.button(
                    icon="help_outline",
                    on_click=lambda _e, k=kind: on_hint(k),
                ).props(
                    "flat dense round size=sm "
                    f'aria-label="Подсказка: {kind}" data-rs-symbol-hint={kind}'
                ).style("color:#A9B8CF;")
                hint.mark(f"rs-hint-{kind}")
                hint.tooltip("Что это и когда применять")


def attach_drag_script(canvas_id) -> None:
    """Включить перетаскивание для палитры и приём на поле диаграммы.

    ``canvas_id`` приходит из NiceGUI как число, а не строка: подставлять
    его в JS нужно через str(). Иначе редактор падал с
    ``TypeError: replace() argument 2 must be str, not int`` и диаграмма
    не открывалась вовсе.
    """
    canvas_key = str(canvas_id)

    # В скрипт подставляется только числовой идентификатор компонента,
    # пользовательский текст в код не попадает. На всякий случай
    # оставляем только цифры и латиницу.
    if not canvas_key.isalnum():
        raise ValueError("Некорректный идентификатор полотна")

    ui.run_javascript(DRAG_SCRIPT.replace("CANVAS_ID", canvas_key))
