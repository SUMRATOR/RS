# RS_DIAGRAM_DIRECTION_FREE_V36
# RS_CANVAS_REFRESH_FIX_V18
# RS_DIAGRAM_EDITOR_V16
"""
Экспериментальный редактор размещений существующей модели.

Модель создаётся штатным сервисом приложения.
Этот модуль не меняет доступность типов моделей.
"""

from __future__ import annotations

# RS_BPMN_SYMBOLS_V39
import uuid

from nicegui import ui
from sqlalchemy import text

from rubik_studio.core.database import get_session_factory

# RS_BPMN_LANE_RENDER_V52
from rubik_studio.core.diagram_symbols_v39 import SYMBOLS as SYMBOLS_V39
from rubik_studio.core.repository import RepositoryService

repository_service = RepositoryService()
# RS_BPMN_SHAPES_V55: единый источник разметки символов —
# палитра, поле и колесо рисуют символ одинаково.
from rubik_studio.core.bpmn_catalog_v55 import (  # noqa: E402 — подключается отдельным блоком
    CATALOG as BPMN_CATALOG_V55,
)
from rubik_studio.core.bpmn_catalog_v55 import (  # noqa: E402 — подключается отдельным блоком
    by_groups as bpmn_groups_v55,
)
from rubik_studio.core.bpmn_events_v58 import (  # noqa: E402 — подключается отдельным блоком
    is_boundary as is_boundary_event_v58,
)
from rubik_studio.core.bpmn_shapes_v55 import (  # noqa: E402 — подключается отдельным блоком
    shape_markup as bpmn_shape_v55,
)
from rubik_studio.core.bpmn_shapes_v55 import (  # noqa: E402 — подключается отдельным блоком
    thumbnail_svg as bpmn_thumb_v55,
)
from rubik_studio.core.diagram_storage_v15 import (  # noqa: E402 — подключается отдельным блоком
    DiagramConflict,
    DiagramStorageError,
    load_diagram,
    save_diagram,
)
from rubik_studio.ui.bpmn_event_palette_v58 import (  # noqa: E402 — подключается отдельным блоком
    render_event_variants_palette,
)
from rubik_studio.ui.pages.canvas_draft_v11 import (  # noqa: E402 — подключается отдельным блоком
    open_canvas_draft as open_technical_draft,
)
from rubik_studio.ui.pages.diagram_smart_links_v23 import (  # noqa: E402 — подключается отдельным блоком
    key as smart_link_key,
)
from rubik_studio.ui.pages.diagram_smart_links_v23 import (  # noqa: E402 — подключается отдельным блоком
    render_svg as render_smart_links_svg,
)

# RS_DIAGRAM_SMART_LINKS_V23


# RS_DIAGRAM_EXPAND_FIELD_V28
WIDTH = 20000
HEIGHT = 20000
NODE_WIDTH = 180
NODE_HEIGHT = 70


def _key(value):
    return uuid.UUID(str(value)).hex


def _message(exc):
    result = str(exc).strip()
    return result or type(exc).__name__


async def _available_models(database_id):
    """
    Получить существующие модели выбранной базы, чей редактор
    в каталоге отмечен AVAILABLE.

    Здесь не создаются модели и не изменяются статусы.
    """
    database_key = _key(database_id)
    factory = get_session_factory()

    async with factory() as session:
        bind = session.get_bind()

        if bind.dialect.name != "sqlite":
            raise DiagramStorageError(
                "Редактор V16 пока поддерживает только SQLite."
            )

        rows = (
            await session.execute(
                text(
                    "SELECT m.id, m.name, t.name "
                    "FROM models AS m "
                    "JOIN model_types AS t ON t.id = m.model_type_id "
                    "WHERE lower(replace(CAST(m.database_id AS TEXT), '-', '')) "
                    "= :database "
                    "AND t.editor_status = 'AVAILABLE' "
                    "ORDER BY m.name, m.id"
                ),
                {"database": database_key},
            )
        ).all()

    return [
        {
            "id": str(row[0]),
            "name": str(row[1]),
            "type_name": str(row[2]),
        }
        for row in rows
    ]


async def open_canvas_draft(database_id, database_name):
    """
    Точка входа для существующей кнопки в карточке базы.

    Позволяет открыть редактор существующей доступной модели
    либо старый технический черновик V13.
    """
    try:
        models = await _available_models(database_id)
    except Exception as exc:
        ui.notify(
            "Не удалось получить список моделей: " + _message(exc),
            type="negative",
            timeout=12000,
        )
        return

    state = {"model_id": None}

    model_options = {
        item["id"]: (
            f"{item['name']} — {item['type_name']} "
            f"[{item['id'][:8]}]"
        )
        for item in models
    }

    async def open_selected():
        model_id = state["model_id"]

        if not model_id:
            ui.notify("Сначала выберите модель.", type="warning")
            return

        selected = next(
            (item for item in models if item["id"] == model_id),
            None,
        )

        if selected is None:
            ui.notify("Модель не найдена в списке.", type="negative")
            return

        dialog.close()
        await open_model_editor(
            database_id,
            database_name,
            selected["id"],
            selected["name"],
        )

    async def open_draft():
        dialog.close()
        await open_technical_draft(database_id, database_name)

    with ui.dialog() as dialog, ui.card().style(
        "width:650px; max-width:95vw;"
    ):
        ui.label(f"Полотно — {database_name}").style(
            "font-size:20px; font-weight:600;"
        )

        ui.label(
            "Выберите существующую модель с доступным редактором. "
            "Размещения будут сохранены в базе данных."
        ).style("color:#94a3b8;")

        if models:
            ui.select(
                options=model_options,
                label="Модель",
                on_change=lambda e: state.update({"model_id": e.value}),
            ).classes("w-full")

            ui.button(
                "Открыть модель",
                icon="open_in_new",
                on_click=open_selected,
            )
        else:
            ui.label(
                "Доступных моделей пока нет. Создайте модель штатным "
                "способом, выбрав доступный тип и методологию."
            ).style("color:#fbbf24;")

        ui.separator()

        ui.label(
            "Технический черновик V13 хранится отдельно в JSON "
            "и не является диаграммой базы."
        ).style("font-size:12px; color:#94a3b8;")

        with ui.row():
            ui.button(
                "Технический черновик",
                on_click=open_draft,
                icon="science",
            ).props("outline")

            ui.button("Закрыть", on_click=dialog.close).props("flat")

    dialog.open()



# RS_BPMN_SHAPES_V41
def _bpmn_shape_markup_v41(kind, name):
    """SVG символа. Пользовательское название экранируется."""
    import html

    title = html.escape(str(name or ""), quote=True)

    event_kinds = {
        "START_EVENT",
        "INTERMEDIATE_EVENT",
        "END_EVENT",
    }
    gateway_kinds = {
        "EXCLUSIVE_GATEWAY",
        "PARALLEL_GATEWAY",
        "INCLUSIVE_GATEWAY",
    }

    if kind in event_kinds:
        stroke_width = 4 if kind == "END_EVENT" else 2
        inner = ""
        if kind == "INTERMEDIATE_EVENT":
            inner = (
                '<circle cx="90" cy="35" r="25" '
                'fill="none" stroke="#86efac" stroke-width="2"/>'
            )

        shape = (
            '<circle cx="90" cy="35" r="29" '
            'fill="#244b43" stroke="#86efac" '
            f'stroke-width="{stroke_width}"/>'
            + inner
        )

    elif kind in gateway_kinds:
        marker = {
            "EXCLUSIVE_GATEWAY": (
                '<path d="M81 26 L99 44 M99 26 L81 44" '
                'fill="none" stroke="#facc15" stroke-width="3"/>'
            ),
            "PARALLEL_GATEWAY": (
                '<path d="M90 24 L90 46 M79 35 L101 35" '
                'fill="none" stroke="#facc15" stroke-width="3"/>'
            ),
            "INCLUSIVE_GATEWAY": (
                '<circle cx="90" cy="35" r="10" '
                'fill="none" stroke="#facc15" stroke-width="3"/>'
            ),
        }[kind]

        shape = (
            '<polygon points="90,5 120,35 90,65 60,35" '
            'fill="#53472a" stroke="#facc15" stroke-width="2"/>'
            + marker
        )

    elif kind in {"PARTICIPANT", "LANE"}:
        # Пока это только графическое обозначение.
        # Настоящие контейнеры с вложенными элементами — отдельный этап.
        shape = (
            '<rect x="1" y="1" width="178" height="68" '
            'fill="#35304b" stroke="#c4b5fd" stroke-width="2"/>'
            '<line x1="27" y1="1" x2="27" y2="69" '
            'stroke="#c4b5fd" stroke-width="2"/>'
        )

    else:
        # Задача и свёрнутый подпроцесс.
        shape = (
            '<rect x="1" y="1" width="178" height="68" '
            'rx="9" ry="9" fill="#273649" '
            'stroke="#93c5fd" stroke-width="2"/>'
        )

        if kind == "SUBPROCESS":
            shape += (
                '<rect x="83" y="51" width="14" height="14" '
                'fill="#273649" stroke="#e2e8f0" stroke-width="1.5"/>'
                '<path d="M86 58 L94 58 M90 54 L90 62" '
                'fill="none" stroke="#e2e8f0" stroke-width="1.5"/>'
            )

    if kind in event_kinds or kind in gateway_kinds:
        label_style = (
            "position:absolute; left:0; top:70px; width:180px;"
            "text-align:center; font-size:12px; line-height:15px;"
            "color:white; overflow-wrap:anywhere;"
            "pointer-events:none;"
        )
    elif kind in {"PARTICIPANT", "LANE"}:
        label_style = (
            "position:absolute; left:33px; top:7px; width:140px;"
            "font-size:13px; line-height:16px; color:white;"
            "overflow:hidden; max-height:55px; overflow-wrap:anywhere;"
            "pointer-events:none;"
        )
    else:
        label_style = (
            "position:absolute; left:9px; top:8px; width:162px;"
            "text-align:center; font-size:13px; line-height:16px;"
            "color:white; overflow:hidden; max-height:40px;"
            "overflow-wrap:anywhere; pointer-events:none;"
        )

    return (
        '<div style="position:relative;width:180px;height:70px;'
        'pointer-events:none;">'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="180" height="70" viewBox="0 0 180 70" '
        'style="display:block;pointer-events:none;">'
        + shape
        + '</svg>'
        + f'<div style="{label_style}">{title}</div>'
        + '</div>'
    )


# RS_BPMN_VISUAL_FIX_V42
_bpmn_shape_before_v42 = _bpmn_shape_markup_v41


def _bpmn_shape_markup_v41(kind, name):
    # Меняем только стандартные названия. Пользовательские
    # переименования остаются нетронутыми.
    default_names = {
        "EXCLUSIVE_GATEWAY": (
            "Исключающий шлюз", "Исключающее ИЛИ"
        ),
        "PARALLEL_GATEWAY": (
            "Параллельный шлюз", "И — все ветви"
        ),
        "INCLUSIVE_GATEWAY": (
            "Включающий шлюз", "И/ИЛИ — одна или несколько ветвей"
        ),
    }

    if kind in default_names:
        old_name, new_name = default_names[kind]
        if name == old_name:
            name = new_name

    markup = _bpmn_shape_before_v42(kind, name)

    # Цвет — дополнительное визуальное различие.
    # Толщина и двойной контур событий сохраняются.
    if kind == "START_EVENT":
        markup = markup.replace("#244b43", "#244b43")
        markup = markup.replace("#86efac", "#86efac")

    elif kind == "INTERMEDIATE_EVENT":
        markup = markup.replace("#244b43", "#4a4123")
        markup = markup.replace("#86efac", "#facc15")

    elif kind == "END_EVENT":
        markup = markup.replace("#244b43", "#512b35")
        markup = markup.replace("#86efac", "#fb7185")

    elif kind == "LANE":
        # Внутренность прозрачная, граница и разделитель остаются.
        markup = markup.replace('fill="#35304b"', 'fill="none"')
        markup = markup.replace('stroke="#c4b5fd"', 'stroke="#94a3b8"')

    elif kind == "PARTICIPANT":
        # Участник визуально отличается от прозрачной дорожки.
        # Это ещё не полноценный масштабируемый пул BPMN.
        markup = markup.replace('fill="#35304b"', 'fill="#2d4161"')
        markup = markup.replace('stroke="#c4b5fd"', 'stroke="#93c5fd"')
        markup = markup.replace(
            'x1="27" y1="1" x2="27" y2="69"',
            'x1="35" y1="1" x2="35" y2="69"',
        )
        markup = markup.replace(
            "left:33px; top:7px; width:140px;",
            "left:42px; top:7px; width:130px;",
        )

    return markup





# RS_BPMN_DATA_SYMBOLS_V48
_bpmn_shape_before_v48 = _bpmn_shape_markup_v41


def _bpmn_shape_markup_v41(kind, name):
    """Дополнительные графические обозначения данных BPMN."""
    import html

    if kind not in {"DATA_INPUT", "DATA_OUTPUT", "DATA_COLLECTION"}:
        return _bpmn_shape_before_v48(kind, name)

    title = html.escape(str(name or ""), quote=True)

    # Объект данных: лист с загнутым углом.
    sheet = (
        '<path d="M70 5 H100 L110 15 V65 H70 Z" '
        'fill="#26394b" stroke="#bfdbfe" '
        'stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M100 5 V15 H110" '
        'fill="none" stroke="#bfdbfe" stroke-width="2" '
        'stroke-linejoin="round"/>'
    )

    if kind == "DATA_INPUT":
        # Вход: контурная стрелка.
        marker = (
            '<path d="M76 21 H89 V17 L96 23 L89 29 V25 H76 Z" '
            'fill="#26394b" stroke="#bfdbfe" '
            'stroke-width="1.5" stroke-linejoin="round"/>'
        )
    elif kind == "DATA_OUTPUT":
        # Выход: заполненная стрелка.
        marker = (
            '<path d="M76 21 H89 V17 L96 23 L89 29 V25 H76 Z" '
            'fill="#bfdbfe" stroke="#bfdbfe" '
            'stroke-width="1.5" stroke-linejoin="round"/>'
        )
    else:
        # Коллекция: три вертикальных штриха.
        marker = (
            '<path d="M84 52 V60 M90 52 V60 M96 52 V60" '
            'fill="none" stroke="#bfdbfe" stroke-width="2"/>'
        )

    return (
        '<div style="position:relative;width:180px;height:70px;'
        'pointer-events:none;">'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="180" height="70" viewBox="0 0 180 70" '
        'style="display:block;pointer-events:none;">'
        + sheet
        + marker
        + '</svg>'
        + '<div style="position:absolute;left:0;top:72px;'
          'width:180px;text-align:center;font-size:12px;'
          'line-height:15px;color:white;overflow-wrap:anywhere;'
          'pointer-events:none;">'
        + title
        + '</div></div>'
    )



# RS_BPMN_LANE_WHEEL_V49
_bpmn_shape_before_v49 = _bpmn_shape_markup_v41


def _bpmn_shape_markup_v41(kind, name):
    import html

    title = html.escape(str(name or ""), quote=True)

    if kind == "LANE":
        # Рамка и подпись не растягиваются масштабированием SVG.
        # Размер задаётся через размер DOM-элемента дорожки.
        return (
            '<div data-rs-lane-frame-v49="1" '
            'style="position:absolute;left:0;top:0;'
            'width:100%;height:100%;box-sizing:border-box;'
            'border:2px solid #94a3b8;background:transparent;'
            'pointer-events:none;">'
            '<div data-rs-lane-title-v49="1" '
            'style="position:absolute;left:0;top:0;'
            'width:34px;height:100%;box-sizing:border-box;'
            'border-right:1px solid #94a3b8;'
            'display:flex;align-items:center;justify-content:center;'
            'writing-mode:vertical-rl;transform:none;'
            'font-size:12px;line-height:16px;color:#e2e8f0;'
            'overflow:hidden;overflow-wrap:anywhere;'
            'pointer-events:none;">'
            + title
            + '</div></div>'
        )

    if kind == "PARTICIPANT":
        # Значок человека в заголовке участника.
        return (
            '<div style="position:relative;width:180px;height:70px;'
            'pointer-events:none;">'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="180" height="70" viewBox="0 0 180 70" '
            'style="display:block;pointer-events:none;">'
            '<rect x="1" y="1" width="178" height="68" '
            'fill="#2d4161" stroke="#93c5fd" stroke-width="2"/>'
            '<line x1="35" y1="1" x2="35" y2="69" '
            'stroke="#93c5fd" stroke-width="1.5"/>'
            '<circle cx="18" cy="26" r="5" '
            'fill="none" stroke="#bfdbfe" stroke-width="2"/>'
            '<path d="M9 46 C9 35 27 35 27 46" '
            'fill="none" stroke="#bfdbfe" stroke-width="2" '
            'stroke-linecap="round"/>'
            '</svg>'
            '<div style="position:absolute;left:42px;top:7px;'
            'width:130px;max-height:55px;overflow:hidden;'
            'font-size:13px;line-height:16px;color:white;'
            'overflow-wrap:anywhere;pointer-events:none;">'
            + title
            + '</div></div>'
        )

    return _bpmn_shape_before_v49(kind, name)


# RS_BPMN_SHAPES_V55
# Полный набор событий и шлюзов рисуется единым модулем bpmn_shapes_v55:
# палитра, поле диаграммы и колесо V используют одну геометрию.
# Старые коды V39 сохранены — ранее сохранённые диаграммы открываются как есть.
_bpmn_shape_before_v55 = _bpmn_shape_markup_v41


def _bpmn_shape_markup_v41(kind, name):
    """Разметка символа BPMN: 43 типа вместо 13.

    Дорожка (LANE) сохраняет реализацию V49: её рамка растягивается по
    размеру DOM-элемента, а не по viewBox.
    """
    if kind == "LANE" or kind not in BPMN_CATALOG_V55:
        return _bpmn_shape_before_v55(kind, name)

    return bpmn_shape_v55(kind, name)


# RS_BPMN_PALETTE_V55
def render_bpmn_palette_v55(on_pick, on_event_pick=None):
    """Палитра символов BPMN для боковой панели редактора.

    Группы: события, работа, ветвление, данные, контейнеры.
    Каждый символ — миниатюра, подпись «термин (пояснение)» и две кнопки:
    добавить на схему и открыть карточку-подсказку.

    Вынесено отдельной функцией, чтобы проверяться без запуска редактора.
    """
    # RS_BPMN_PALETTE_V55
    # Палитра символов BPMN по группам: события, работа,
    # ветвление, данные. Подпись — «термин (пояснение)»,
    # для каждого символа доступна карточка-подсказка.
    # Существующее радиальное колесо по клавише V сохранено.
    ui.label("Символы").style(
        "font-size:16px; font-weight:600;"
    )

    ui.label(
        "Нажмите на символ, чтобы добавить его на схему. "
        "Подробное описание — в подсказке под названием."
    ).style("font-size:12px; color:#94a3b8; line-height:15px;")

    def insert_symbol_v55(kind):
        on_pick(kind)

    def show_hint_v55(kind):
        info = BPMN_CATALOG_V55.get(kind) or {}
        with ui.dialog() as hint_dialog, ui.card().style(
            "width:32rem; max-width:92vw; gap:10px; padding:18px;"
        ):
            with ui.row().classes("items-center gap-3 no-wrap"):
                ui.html(bpmn_thumb_v55(kind, 56), sanitize=False)
                ui.label(info.get("label", kind)).style(
                    "font-size:16px; font-weight:600; line-height:20px;"
                )

            ui.label(info.get("hint", "")).style(
                "font-size:14px; line-height:20px;"
            )

            example = info.get("example")
            if example:
                ui.label(f"Пример: {example}").style(
                    "font-size:13px; color:#94a3b8;"
                )

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(
                    "Понятно",
                    on_click=hint_dialog.close,
                ).props("flat")

                ui.button(
                    "Добавить на схему",
                    icon="add",
                    on_click=lambda: (
                        hint_dialog.close(),
                        insert_symbol_v55(kind),
                    ),
                ).props("color=primary")

        hint_dialog.open()

    for group_name_v55, group_items_v55 in bpmn_groups_v55():
        ui.label(group_name_v55).style(
            "font-size:12px; font-weight:700; letter-spacing:.05em; "
            "text-transform:uppercase; color:#7c8da8; margin-top:6px;"
        )

        grid_v55 = ui.element("div").style(
            "display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); "
            "gap:6px; width:100%;"
        )
        with grid_v55:
            for kind_v55, label_v55 in group_items_v55:
                with ui.element("div").style(
                    "display:flex; flex-direction:column; align-items:center; "
                    "gap:2px; padding:6px 4px; border-radius:10px; "
                    "background:#1E2B45; border:1px solid #33415C; "
                ):
                    ui.html(
                        bpmn_thumb_v55(kind_v55, 40),
                        sanitize=False,
                    ).style("height:40px; display:flex; align-items:center;")

                    ui.label(
                        BPMN_CATALOG_V55[kind_v55]["label"]
                    ).style(
                        "font-size:11px; line-height:13px; "
                        "text-align:center; color:#E8EDF5;"
                    )

                    with ui.row().classes("gap-1 no-wrap"):
                        # aria-label позволяет найти конкретный символ в
                        # автотестах и помогает программам чтения с экрана.
                        add_button_v55 = ui.button(
                            icon="add",
                            on_click=lambda k=kind_v55: insert_symbol_v55(k),
                        ).props(
                            "flat dense round size=sm "
                            f'aria-label="Добавить: {kind_v55}" '
                            f"data-rs-symbol-add={kind_v55}"
                        ).style("color:#7FB2FF;")
                        add_button_v55.mark(f"rs-add-{kind_v55}")
                        add_button_v55.tooltip("Добавить на схему")

                        help_button_v55 = ui.button(
                            icon="help_outline",
                            on_click=lambda k=kind_v55: show_hint_v55(k),
                        ).props(
                            "flat dense round size=sm "
                            f'aria-label="Подсказка: {kind_v55}" '
                            f"data-rs-symbol-hint={kind_v55}"
                        ).style("color:#A9B8CF;")
                        help_button_v55.mark(f"rs-hint-{kind_v55}")
                        help_button_v55.tooltip("Что это и когда применять")

    ui.separator()

    # RS_BPMN_EVENT_VARIANTS_V58
    # Палитра вариантов событий: вкладки «Начальное / Промежуточное /
    # Граничное / Конечное» и выбор подтипа. Граничные события крепятся
    # к границе задачи — редактор создаёт их в режиме привязки.
    if on_event_pick is not None:
        render_event_variants_palette(
            on_pick=on_event_pick,
            on_hint=show_hint_v55,
        )

    ui.separator()


def _insert_event_v58(kind, insert_symbol) -> None:
    """Добавить событие из палитры вариантов.

    Для граничных событий сразу объясняем, что они крепятся к задаче:
    без этого пользователь ставит их на поле и не понимает, почему
    событие «висит» отдельно.
    """
    if is_boundary_event_v58(kind):
        ui.notify(
            "Граничное событие крепится к границе задачи: "
            "выделите задачу на схеме, затем выберите событие.",
            type="info",
        )
    insert_symbol(kind)


async def open_model_editor(
    database_id,
    database_name,
    model_id,
    model_name,
):
    try:
        content = await load_diagram(database_id, model_id)
        objects = await repository_service.list_objects(database_id)
        repository_links = await repository_service.list_links(database_id)
    except Exception as exc:
        ui.notify(
            "Не удалось открыть модель: " + _message(exc),
            type="negative",
            timeout=12000,
        )
        return

    state = {
        "revision": content["revision"],
        "nodes": content["nodes"],
        "edges": content["edges"],
        "repository_links": [
            {
                "source_id": str(link.source_id),
                "target_id": str(link.target_id),
                "link_type": str(link.link_type),
            }
            for link in repository_links
        ],
        "objects": {str(obj.id): str(obj.name) for obj in objects},
        "selected_object": None,
        "selected_node": None,
        "dirty": False,
        "saving": False,
    }

    object_options = {
        str(obj.id): f"{obj.name} [{str(obj.id)[:8]}]"
        for obj in objects
    }

    def node_options():
        result = {}

        for node in state["nodes"]:
            name = node.get("name") or "Объект"
            result[node["id"]] = f"{name} [{node['id'][:8]}]"

        return result

    def update_node_selector():
        selector.options = node_options()

        if state["selected_node"] not in selector.options:
            state["selected_node"] = None
            selector.value = None

        selector.update()

        # RS_DIAGRAM_FLOW_TYPES_V29_SELECTORS
        for flow_selector, key_name in (
            (flow_source_selector, "source"),
            (flow_target_selector, "target"),
        ):
            flow_selector.options = node_options()
            if flow_state[key_name] not in flow_selector.options:
                flow_state[key_name] = None
                flow_selector.value = None
            flow_selector.update()

    def mark_dirty():
        state["dirty"] = True
        status.set_text("Есть несохранённые изменения")

    def on_move(node_id, event):
        # RS_BPMN_LANE_SIZE_V45: проверка фактических размеров.
        import math

        detail = event.args
        if isinstance(detail, dict) and "detail" in detail:
            detail = detail["detail"]
        if not isinstance(detail, dict):
            return

        try:
            x = float(detail["x"])
            y = float(detail["y"])
        except (KeyError, TypeError, ValueError, OverflowError):
            return

        if not math.isfinite(x) or not math.isfinite(y):
            return

        for node in state["nodes"]:
            if node["id"] != node_id:
                continue

            try:
                width = float(node.get("width", NODE_WIDTH))
                height = float(node.get("height", NODE_HEIGHT))
            except (TypeError, ValueError, OverflowError):
                return

            if not math.isfinite(width) or not math.isfinite(height):
                return
            if width <= 0 or height <= 0:
                return
            if not (0 <= x <= WIDTH - width):
                return
            if not (0 <= y <= HEIGHT - height):
                return

            if node["x"] != x or node["y"] != y:
                node["x"] = x
                node["y"] = y
                mark_dirty()
            break


    # RS_DIAGRAM_CHAIN_EDITOR_V32
    def open_chain_editor_v32(event):
        detail = event.args

        if isinstance(detail, dict) and "detail" in detail:
            detail = detail["detail"]

        if not isinstance(detail, dict):
            ui.notify("Не удалось получить выделение.", type="warning")
            return

        selected = detail.get("nodes")

        if not isinstance(selected, list):
            ui.notify("Не удалось получить список объектов.", type="warning")
            return

        # V31 передаёт UUID в нормализованном виде.
        by_key = {}
        try:
            for node in state["nodes"]:
                by_key[smart_link_key(node["id"])] = node
        except Exception:
            ui.notify("Некорректный идентификатор элемента.", type="negative")
            return

        selected_nodes = []
        seen = set()

        for item in selected:
            try:
                key = smart_link_key(item)
            except Exception:
                ui.notify("Некорректное выделение.", type="warning")
                return

            if key in seen:
                continue

            node = by_key.get(key)
            if node is None:
                ui.notify(
                    "Выделение устарело. Выделите объекты заново.",
                    type="warning",
                )
                return

            seen.add(key)
            selected_nodes.append(node)

        if len(selected_nodes) < 2:
            ui.notify(
                "Выделите минимум два объекта через Shift + ЛКМ.",
                type="warning",
            )
            return

        kinds = {
            "MESSAGE": "Поток сообщений",
            "CONTROL": "Поток управления",
            "DEFAULT": 'Поток управления «в остальных случаях»',
            "CONDITIONAL": "Условный поток управления",
        }

        options = {
            str(node["id"]): (
                f"{node.get('name') or 'Объект'} "
                f"[{str(node['id'])[:8]}]"
            )
            for node in selected_nodes
        }

        draft = {
            "common": "CONTROL",
            "source": str(selected_nodes[0]["id"]),
            "target": str(selected_nodes[1]["id"]),
            "rows": [
                {
                    "source": str(selected_nodes[index]["id"]),
                    "target": str(selected_nodes[index + 1]["id"]),
                    "kind": "CONTROL",
                }
                for index in range(len(selected_nodes) - 1)
            ],
        }

        def apply_common():
            kind = draft["common"]

            if kind not in kinds:
                ui.notify("Выберите тип потока.", type="warning")
                return

            for row in draft["rows"]:
                row["kind"] = kind

            draw_rows.refresh()

        def add_pair():
            source_id = draft["source"]
            target_id = draft["target"]

            if source_id not in options or target_id not in options:
                ui.notify("Выберите два объекта.", type="warning")
                return

            if source_id == target_id:
                ui.notify(
                    "Начало и конец должны быть разными объектами.",
                    type="warning",
                )
                return

            draft["rows"].append({
                "source": source_id,
                "target": target_id,
                "kind": draft["common"],
            })
            draw_rows.refresh()

        def remove_row(index):
            if 0 <= index < len(draft["rows"]):
                draft["rows"].pop(index)
                draw_rows.refresh()

        def set_row_kind(index, value):
            if 0 <= index < len(draft["rows"]) and value in kinds:
                draft["rows"][index]["kind"] = value

        @ui.refreshable
        def draw_rows():
            if not draft["rows"]:
                ui.label("В списке пока нет связей.").style(
                    "color:#64748b;"
                )
                return

            for index, row in enumerate(draft["rows"]):
                with ui.row().classes("w-full items-center no-wrap"):
                    ui.label(
                        f"{index + 1}. "
                        f"{options.get(row['source'], '?')} → "
                        f"{options.get(row['target'], '?')}"
                    ).style(
                        "flex:1; min-width:180px; "
                        "overflow-wrap:anywhere;"
                    )

                    ui.select(
                        options=kinds,
                        value=row["kind"],
                        on_change=lambda e, i=index: set_row_kind(i, e.value),
                    ).style("width:240px; min-width:180px;")

                    ui.button(
                        icon="delete_outline",
                        on_click=lambda i=index: remove_row(i),
                    ).props("flat round dense").tooltip(
                        "Убрать эту связь из списка"
                    )

        def create_flows():
            if state["saving"]:
                ui.notify(
                    "Дождитесь окончания сохранения.",
                    type="warning",
                )
                return

            if not draft["rows"]:
                ui.notify("Добавьте хотя бы одну связь.", type="warning")
                return

            if len(state["edges"]) + len(draft["rows"]) > 2000:
                ui.notify(
                    "Превышен предел в 2000 линий.",
                    type="warning",
                )
                return

            # Проверяем актуальное состояние, а не только снимок,
            # сделанный при открытии редактора.
            current = {
                str(node["id"]): node for node in state["nodes"]
            }

            new_edges = []

            for index, row in enumerate(draft["rows"], 1):
                source_id = row["source"]
                target_id = row["target"]
                kind = row["kind"]

                if kind not in kinds:
                    ui.notify(
                        f"Строка {index}: выберите тип потока.",
                        type="warning",
                    )
                    return

                if source_id == target_id:
                    ui.notify(
                        f"Строка {index}: объекты должны быть разными.",
                        type="warning",
                    )
                    return

                source_node = current.get(source_id)
                target_node = current.get(target_id)

                if source_node is None or target_node is None:
                    ui.notify(
                        "Один из элементов удалён. "
                        "Закройте редактор и выделите объекты заново.",
                        type="warning",
                    )
                    return

                try:
                    # Координаты не нужны для связи, но проверяем, что они
                    # числа: иначе линия не построится и редактор «зависнет».
                    for checked_node in (source_node, target_node):
                        float(checked_node["x"])
                        float(checked_node.get("width", NODE_WIDTH))
                except (KeyError, TypeError, ValueError):
                    ui.notify(
                        f"Строка {index}: некорректные координаты.",
                        type="negative",
                    )
                    return


                new_edges.append({
                    "id": uuid.uuid4().hex,
                    "source_node_id": source_id,
                    "target_node_id": target_id,
                    "label": "__RS_FLOW_V29__:" + kind,
                })

            # До этого места состояние диаграммы не изменяется.
            state["edges"].extend(new_edges)
            mark_dirty()
            chain_dialog.close()
            draw_canvas.refresh()

            ui.notify(
                f"Создано потоков: {len(new_edges)}. "
                "Сохраните диаграмму.",
                type="positive",
            )

        with ui.dialog() as chain_dialog, ui.card().style(
            "width:950px; max-width:95vw; "
            "max-height:90vh; overflow:auto;"
        ):
            chain_dialog.props("persistent")

            ui.label("Создать связи").style(
                "font-size:20px; font-weight:600;"
            )

            ui.label(
                "Цепь составлена в порядке выделения. "
                "Общий тип применяется ко всем строкам; "
                "тип каждой строки можно изменить отдельно."
            ).style("color:#64748b;")

            with ui.row().classes("w-full items-center"):
                ui.select(
                    options=kinds,
                    value=draft["common"],
                    label="Общий тип",
                    on_change=lambda e: draft.update(
                        {"common": e.value}
                    ),
                ).style("min-width:260px;")

                ui.button(
                    "Применить ко всем",
                    on_click=apply_common,
                ).props("outline")

            ui.separator()

            ui.label("Связи в цепи").style("font-weight:600;")
            draw_rows()

            ui.separator()

            ui.label("Добавить связь между выделенными объектами").style(
                "font-weight:600;"
            )

            with ui.row().classes("w-full items-center"):
                ui.select(
                    options=options,
                    value=draft["source"],
                    label="Начало",
                    on_change=lambda e: draft.update(
                        {"source": e.value}
                    ),
                ).style("min-width:220px; flex:1;")

                ui.select(
                    options=options,
                    value=draft["target"],
                    label="Конец",
                    on_change=lambda e: draft.update(
                        {"target": e.value}
                    ),
                ).style("min-width:220px; flex:1;")

                ui.button(
                    "Добавить пару",
                    icon="add",
                    on_click=add_pair,
                ).props("outline")

            ui.label(
                "Направление задаётся выбранными началом и концом. "
                "Технические связи репозитория не изменяются."
            ).style("font-size:12px; color:#64748b;")

            with ui.row():
                ui.button(
                    "Создать потоки",
                    icon="arrow_forward",
                    on_click=create_flows,
                )
                ui.button(
                    "Отмена",
                    on_click=chain_dialog.close,
                ).props("flat")

        chain_dialog.open()


    # RS_DIAGRAM_EDIT_FLOW_V33
    def open_flow_editor_v33(event):
        detail = event.args

        if isinstance(detail, dict) and "detail" in detail:
            detail = detail["detail"]

        if not isinstance(detail, dict):
            return

        try:
            edge_key = smart_link_key(detail.get("edge_id"))
        except Exception:
            ui.notify("Не удалось определить выбранную линию.", type="warning")
            return

        matches = []

        for edge in state["edges"]:
            try:
                if smart_link_key(edge["id"]) == edge_key:
                    matches.append(edge)
            except Exception:
                continue

        if len(matches) != 1:
            ui.notify(
                "Линия не найдена или её идентификатор неоднозначен.",
                type="warning",
            )
            return

        edge = matches[0]
        prefix = "__RS_FLOW_V29__:"

        kinds = {
            "MESSAGE": "Поток сообщений",
            "CONTROL": "Поток управления",
            "DEFAULT": 'Поток управления «в остальных случаях»',
            "CONDITIONAL": "Условный поток управления",
        }

        label = str(edge.get("label") or "")

        if not label.startswith(prefix):
            ui.notify(
                "Эта линия не является потоком V29.",
                type="warning",
            )
            return

        current_kind = label[len(prefix):]

        if current_kind not in kinds:
            ui.notify(
                "Неизвестный тип потока. Линия не изменена.",
                type="warning",
            )
            return

        choice = {"kind": current_kind}

        def apply_choice():
            if state["saving"]:
                ui.notify(
                    "Дождитесь окончания сохранения.",
                    type="warning",
                )
                return

            kind = choice["kind"]

            if kind not in kinds:
                ui.notify("Выберите тип потока.", type="warning")
                return

            # Проверяем, что линия не исчезла после открытия окна.
            current_matches = []

            for item in state["edges"]:
                try:
                    if smart_link_key(item["id"]) == edge_key:
                        current_matches.append(item)
                except Exception:
                    continue

            if len(current_matches) != 1:
                ui.notify(
                    "Линия больше недоступна.",
                    type="warning",
                )
                flow_dialog.close()
                return

            current_edge = current_matches[0]
            new_label = prefix + kind

            if current_edge.get("label") != new_label:
                current_edge["label"] = new_label
                mark_dirty()
                draw_canvas.refresh()
                ui.notify(
                    "Тип потока изменён. Сохраните диаграмму.",
                    type="positive",
                )

            flow_dialog.close()

        # RS_DIAGRAM_FLOW_DELETE_V44
        def delete_flow_v44():
            if state["saving"]:
                ui.notify(
                    "Дождитесь окончания сохранения.",
                    type="warning",
                )
                return

            matches_v44 = []
            for item in state["edges"]:
                try:
                    if smart_link_key(item["id"]) == edge_key:
                        matches_v44.append(item)
                except Exception:
                    continue

            if len(matches_v44) != 1:
                ui.notify(
                    "Линия больше недоступна.",
                    type="warning",
                )
                flow_dialog.close()
                return

            current = matches_v44[0]
            current_label = str(current.get("label") or "")

            # Не удаляем технические связи или старые линии V14.
            if current_label not in {
                "__RS_FLOW_V29__:MESSAGE",
                "__RS_FLOW_V29__:CONTROL",
                "__RS_FLOW_V29__:DEFAULT",
                "__RS_FLOW_V29__:CONDITIONAL",
            }:
                ui.notify(
                    "Эта линия не является редактируемым потоком.",
                    type="warning",
                )
                return

            state["edges"].remove(current)
            mark_dirty()
            flow_dialog.close()
            draw_canvas.refresh()

            ui.notify(
                "Поток удалён с диаграммы. Сохраните изменения.",
                type="positive",
            )

        with ui.dialog() as flow_dialog, ui.card().style(
            "width:480px; max-width:95vw;"
        ):
            flow_dialog.props("persistent")

            ui.label("Выбрать связь").style(
                "font-size:20px; font-weight:600;"
            )

            ui.select(
                options=kinds,
                value=current_kind,
                label="Тип потока",
                on_change=lambda e: choice.update({"kind": e.value}),
            ).classes("w-full")

            ui.label(
                "Изменение применяется только к выбранной линии. "
                "После изменения сохраните диаграмму."
            ).style("font-size:12px; color:#64748b;")

            with ui.row():
                ui.button("Применить", on_click=apply_choice)
                ui.button(
                    "Удалить поток",
                    icon="delete_outline",
                    color="negative",
                    on_click=delete_flow_v44,
                ).props("outline")
                ui.button(
                    "Отмена",
                    on_click=flow_dialog.close,
                ).props("flat")

        flow_dialog.open()


    # RS_DIAGRAM_RADIAL_MENU_V37
    def open_radial_import_v37(event):
        detail = event.args

        if isinstance(detail, dict) and "detail" in detail:
            detail = detail["detail"]

        if not isinstance(detail, dict):
            ui.notify("Не удалось определить точку импорта.", type="warning")
            return

        try:
            center_x = float(detail["x"])
            center_y = float(detail["y"])
        except (KeyError, TypeError, ValueError):
            ui.notify("Некорректные координаты импорта.", type="warning")
            return

        # Размещение сохраняет текущие ограничения V15/V28.
        x = center_x - NODE_WIDTH / 2
        y = center_y - NODE_HEIGHT / 2

        if not (0 <= x <= WIDTH - NODE_WIDTH):
            ui.notify(
                "Точка импорта за горизонтальной границей поля.",
                type="warning",
            )
            return

        if not (0 <= y <= HEIGHT - NODE_HEIGHT):
            ui.notify(
                "Точка импорта за вертикальной границей поля.",
                type="warning",
            )
            return

        choice = {"object_id": None}

        def add_selected():
            if state["saving"]:
                ui.notify(
                    "Дождитесь окончания сохранения.",
                    type="warning",
                )
                return

            object_id = choice["object_id"]

            if not object_id or object_id not in state["objects"]:
                ui.notify("Выберите объект репозитория.", type="warning")
                return

            if len(state["nodes"]) >= 500:
                ui.notify("Достигнут предел элементов.", type="warning")
                return

            node = {
                "id": uuid.uuid4().hex,
                "object_id": object_id,
                "name": state["objects"][object_id],
                "x": x,
                "y": y,
                "width": NODE_WIDTH,
                "height": NODE_HEIGHT,
            }

            state["nodes"].append(node)
            state["selected_node"] = node["id"]
            mark_dirty()
            update_node_selector()
            selector.value = node["id"]
            selector.update()
            import_dialog.close()
            draw_canvas.refresh()

            ui.notify(
                "Объект добавлен. Сохраните диаграмму.",
                type="positive",
            )

        with ui.dialog() as import_dialog, ui.card().style(
            "width:480px; max-width:95vw;"
        ):
            import_dialog.props("persistent")
            ui.label("Импорт объекта").style(
                "font-size:20px; font-weight:600;"
            )
            ui.select(
                options=object_options,
                label="Объект репозитория",
                on_change=lambda e: choice.update(
                    {"object_id": e.value}
                ),
            ).classes("w-full")
            with ui.row():
                ui.button("Добавить", icon="add", on_click=add_selected)
                ui.button("Отмена", on_click=import_dialog.close).props("flat")

        import_dialog.open()

    # RS_BPMN_SYMBOLS_V39
    symbol_choice_v39 = {"kind": "TASK"}

    def add_symbol_v39(kind, center_x=None, center_y=None):
        if state["saving"]:
            ui.notify("Дождитесь окончания сохранения.", type="warning")
            return

        if kind not in SYMBOLS_V39:
            ui.notify("Выберите символ.", type="warning")
            return

        if len(state["nodes"]) >= 500:
            ui.notify("Достигнут предел элементов.", type="warning")
            return

        if center_x is None or center_y is None:
            index = len(state["nodes"])
            x = 20 + (index % 4) * 210
            y = 20 + ((index // 4) % 5) * 90
        else:
            try:
                x = float(center_x) - NODE_WIDTH / 2
                y = float(center_y) - NODE_HEIGHT / 2
            except (TypeError, ValueError):
                ui.notify("Некорректная точка размещения.", type="warning")
                return

        if not (0 <= x <= WIDTH - NODE_WIDTH):
            ui.notify("Точка за горизонтальной границей поля.", type="warning")
            return

        if not (0 <= y <= HEIGHT - NODE_HEIGHT):
            ui.notify("Точка за вертикальной границей поля.", type="warning")
            return

        node = {
            "id": uuid.uuid4().hex,
            "object_id": None,
            "symbol_type": kind,
            "name": SYMBOLS_V39[kind],
            "x": x,
            "y": y,
            "width": NODE_WIDTH,
            "height": NODE_HEIGHT,
        }

        state["nodes"].append(node)
        state["selected_node"] = node["id"]
        mark_dirty()
        update_node_selector()
        selector.value = node["id"]
        selector.update()
        draw_canvas.refresh()

        ui.notify(
            "Символ добавлен. Сохраните диаграмму.",
            type="positive",
        )

    def radial_symbol_v39(event):
        detail = event.args
        if isinstance(detail, dict) and "detail" in detail:
            detail = detail["detail"]

        if not isinstance(detail, dict):
            ui.notify("Не удалось получить точку размещения.", type="warning")
            return

        add_symbol_v39(
            detail.get("kind"),
            detail.get("x"),
            detail.get("y"),
        )

    def rename_symbol_v39():
        node_id = state["selected_node"]
        node = next(
            (item for item in state["nodes"] if item["id"] == node_id),
            None,
        )

        if not node or not node.get("symbol_type"):
            ui.notify(
                "В списке размещений выберите самостоятельный символ.",
                type="warning",
            )
            return

        # RS_BPMN_LANE_SIZE_V45
        choice = {
            "name": str(node.get("name") or ""),
            "width": node.get("width", NODE_WIDTH),
            "height": node.get("height", NODE_HEIGHT),
        }

        def apply_name():
            if state["saving"]:
                ui.notify("Дождитесь окончания сохранения.", type="warning")
                return

            name = choice["name"]
            if not isinstance(name, str) or len(name) > 500:
                ui.notify("Название должно быть не длиннее 500 знаков.", type="warning")
                return

            current = next(
                (item for item in state["nodes"] if item["id"] == node_id),
                None,
            )
            if current is None or not current.get("symbol_type"):
                ui.notify("Символ больше недоступен.", type="warning")
                rename_dialog.close()
                return

            if current.get("symbol_type") == "LANE":
                try:
                    width = float(choice["width"])
                    height = float(choice["height"])
                except (TypeError, ValueError):
                    ui.notify(
                        "Введите ширину и высоту дорожки.",
                        type="warning",
                    )
                    return

                import math

                if (
                    not math.isfinite(width)
                    or not math.isfinite(height)
                    or width < 100
                    or height < 70
                    or width > WIDTH
                    or height > HEIGHT
                    or float(current["x"]) + width > WIDTH
                    or float(current["y"]) + height > HEIGHT
                ):
                    ui.notify(
                        "Дорожка должна иметь размер не менее 100 × 70 "
                        "и помещаться в текущих границах поля.",
                        type="warning",
                        timeout=10000,
                    )
                    return

                current["width"] = width
                current["height"] = height

            current["name"] = name.strip()
            mark_dirty()
            update_node_selector()
            draw_canvas.refresh()
            rename_dialog.close()

        with ui.dialog() as rename_dialog, ui.card().style(
            "width:480px; max-width:95vw;"
        ):
            rename_dialog.props("persistent")
            ui.label("Название символа")
            if node.get("symbol_type") == "LANE":
                ui.label(
                    "Размер дорожки в единицах поля"
                ).style("font-size:12px; color:#64748b;")
                with ui.row().classes("w-full"):
                    ui.number(
                        "Ширина",
                        value=choice["width"],
                        min=100,
                        on_change=lambda e: choice.update(
                            {"width": e.value}
                        ),
                    ).style("flex:1; min-width:120px;")
                    ui.number(
                        "Высота",
                        value=choice["height"],
                        min=70,
                        on_change=lambda e: choice.update(
                            {"height": e.value}
                        ),
                    ).style("flex:1; min-width:120px;")
            ui.input(
                value=choice["name"],
                on_change=lambda e: choice.update({"name": e.value}),
            ).classes("w-full").props("maxlength=500")
            with ui.row():
                ui.button("Применить", on_click=apply_name)
                ui.button("Отмена", on_click=rename_dialog.close).props("flat")

        rename_dialog.open()


    # RS_BPMN_LANE_WHEEL_V49
    def resize_lane_v49(node_id, event):
        import math

        if state["saving"]:
            ui.notify(
                "Дождитесь окончания сохранения и повторите изменение размера.",
                type="warning",
            )
            draw_canvas.refresh()
            return

        detail = event.args
        if isinstance(detail, dict) and "detail" in detail:
            detail = detail["detail"]

        if not isinstance(detail, dict):
            draw_canvas.refresh()
            return

        node = next(
            (
                item for item in state["nodes"]
                if item["id"] == node_id
                and item.get("symbol_type") == "LANE"
            ),
            None,
        )

        if node is None:
            draw_canvas.refresh()
            return

        try:
            width = float(detail["width"])
            height = float(detail["height"])
            x = float(node["x"])
            y = float(node["y"])
        except (KeyError, TypeError, ValueError, OverflowError):
            draw_canvas.refresh()
            return

        if (
            not all(math.isfinite(v) for v in (width, height, x, y))
            or width < 100
            or height < 70
            or x + width > WIDTH
            or y + height > HEIGHT
        ):
            ui.notify(
                "Недопустимый размер дорожки.",
                type="warning",
            )
            draw_canvas.refresh()
            return

        if node.get("width") != width or node.get("height") != height:
            node["width"] = width
            node["height"] = height
            mark_dirty()

        draw_canvas.refresh()

    @ui.refreshable
    def draw_canvas():
        with ui.element("div").style(
            f"position:relative; width:{WIDTH}px; height:{HEIGHT}px; "
            f"min-width:{WIDTH}px; overflow:hidden; "
            "border:1px solid #33415C; border-radius:10px; "
            "background-color:#17202c; "
            "background-image:"
            "linear-gradient(#ffffff0a 1px, transparent 1px),"
            "linear-gradient(90deg, #ffffff0a 1px, transparent 1px);"
            "background-size:25px 25px;"
        ) as canvas:

            # RS_DIAGRAM_PAN_ZOOM_V25
            canvas.on(
                "rs-radial-symbol-v39",
                radial_symbol_v39,
                args=["detail"],
            )
            canvas.on(
                "rs-radial-import-v37",
                open_radial_import_v37,
                args=["detail"],
            )
            canvas.on(
                "rs-edit-flow-v33",
                open_flow_editor_v33,
                args=["detail"],
            )
            canvas.on(
                "rs-open-chain-v32",
                open_chain_editor_v32,
                args=["detail"],
            )
            pan_zoom_script = """
            (() => {
                const canvasId = 'cCANVAS_ID';

                // Сохраняем положение обзора между refresh полотна.
                const shared = window.__rsDiagramViewV25 ||= {
                    x: 0,
                    y: 0,
                    scale: 1,
                    controller: null
                };

                let attempts = 0;

                function attach() {
                    const canvas = document.getElementById(canvasId);

                    if (!canvas || !canvas.parentElement) {
                        attempts += 1;
                        if (attempts < 80) {
                            setTimeout(attach, 50);
                        }
                        return;
                    }

                    // При обновлении полотна удаляем старые обработчики.
                    if (shared.controller) {
                        shared.controller.abort();
                    }

                    const controller = new AbortController();
                    shared.controller = controller;
                    const signal = controller.signal;

                    const viewport = canvas.parentElement;

                    viewport.style.position = 'relative';
                    viewport.style.width = '100%';
                    viewport.style.height = 'auto';
                    viewport.style.minHeight = '0';
                    viewport.style.overflow = 'hidden';
                    viewport.style.background = '#101925';
                    viewport.style.border = '1px solid #526174';
                    viewport.style.borderRadius = '0';

                    canvas.style.transformOrigin = '0 0';
                    canvas.style.margin = '0';
                    canvas.style.willChange = 'transform';

                    let spacePressed = false;
                    let panning = false;
                    let pointerId = null;
                    let startX = 0;
                    let startY = 0;
                    let viewX = 0;
                    let viewY = 0;

                    function applyView() {
                        canvas.style.transform =
                            `translate(${shared.x}px, ${shared.y}px) ` +
                            `scale(${shared.scale})`;

                        canvas.dataset.rsViewScale = String(shared.scale);
                    }

                    function editableTarget(target) {
                        if (!(target instanceof Element)) return false;
                        return Boolean(target.closest(
                            'input, textarea, select, ' +
                            '[contenteditable="true"], [role="textbox"]'
                        ));
                    }

                    document.addEventListener('keydown', event => {
                        if (
                            event.code !== 'Space' ||
                            editableTarget(event.target)
                        ) {
                            return;
                        }

                        // Не перехватываем пробел вне области редактора,
                        // если курсор не находится над полем.
                        if (!viewport.matches(':hover')) return;

                        event.preventDefault();
                        spacePressed = true;
                        viewport.style.cursor = 'grab';
                    }, {signal});

                    document.addEventListener('keyup', event => {
                        if (event.code !== 'Space') return;

                        spacePressed = false;

                        if (!panning) {
                            viewport.style.cursor = '';
                        }
                    }, {signal});

                    window.addEventListener('blur', () => {
                        spacePressed = false;
                        panning = false;
                        pointerId = null;
                        viewport.style.cursor = '';
                    }, {signal});

                    // Capture нужен, чтобы пробел + перетаскивание узла
                    // перемещало поле, а не сам узел.
                    viewport.addEventListener('pointerdown', event => {
                        if (
                            !spacePressed ||
                            event.button !== 0
                        ) {
                            return;
                        }

                        event.preventDefault();
                        event.stopImmediatePropagation();

                        panning = true;
                        pointerId = event.pointerId;

                        startX = event.clientX;
                        startY = event.clientY;

                        viewX = shared.x;
                        viewY = shared.y;

                        viewport.style.cursor = 'grabbing';

                        try {
                            viewport.setPointerCapture(pointerId);
                        } catch (_) {
                            // Обработчики document ниже всё равно
                            // завершат операцию.
                        }
                    }, {capture: true, signal});

                    document.addEventListener('pointermove', event => {
                        if (!panning || event.pointerId !== pointerId) {
                            return;
                        }

                        event.preventDefault();

                        shared.x = viewX + event.clientX - startX;
                        shared.y = viewY + event.clientY - startY;

                        applyView();
                    }, {capture: true, signal});

                    function finishPan(event) {
                        if (!panning) return;

                        if (
                            event &&
                            event.pointerId !== undefined &&
                            event.pointerId !== pointerId
                        ) {
                            return;
                        }

                        panning = false;
                        pointerId = null;

                        viewport.style.cursor = spacePressed ? 'grab' : '';
                    }

                    document.addEventListener(
                        'pointerup',
                        finishPan,
                        {capture: true, signal}
                    );

                    document.addEventListener(
                        'pointercancel',
                        finishPan,
                        {capture: true, signal}
                    );

                    viewport.addEventListener('wheel', event => {
                        event.preventDefault();

                        const rect = viewport.getBoundingClientRect();

                        const px = event.clientX - rect.left;
                        const py = event.clientY - rect.top;

                        const oldScale = shared.scale;
                        const factor = Math.exp(-event.deltaY * 0.001);

                        const newScale = Math.max(
                            0.25,
                            Math.min(3.0, oldScale * factor)
                        );

                        // Точка под курсором остаётся на том же месте.
                        const worldX = (px - shared.x) / oldScale;
                        const worldY = (py - shared.y) / oldScale;

                        shared.scale = newScale;
                        shared.x = px - worldX * newScale;
                        shared.y = py - worldY * newScale;

                        applyView();
                    }, {passive: false, signal});


                    // RS_DIAGRAM_PORT_CLICK_V47_SCOPE_FIX
                    function clearPortStartV47() {
                        delete canvas.dataset.rsPortStartV47;
                        viewport.style.cursor = '';
                    }

                    document.addEventListener('keydown', event => {
                        if (
                            event.key === 'Escape' &&
                            canvas.dataset.rsPortStartV47
                        ) {
                            clearPortStartV47();
                            event.preventDefault();
                            event.stopImmediatePropagation();
                        }
                    }, {capture: true, signal});

                    signal.addEventListener('abort', () => {
                        clearPortStartV47();
                    }, {once: true});

                    // RS_DIAGRAM_SELECTION_V31

                    // RS_DIAGRAM_EDIT_FLOW_V33
                    // Делаем широкие невидимые области нажатия,
                    // не изменяя видимую толщину линий.
                    const flowHitObserversV33 = [];

                    function attachFlowHitsV33() {
                        canvas.querySelectorAll(
                            '.rs-smart-line[data-rs-flow-edge]'
                        ).forEach(group => {
                            if (group.dataset.rsFlowHitReady === '1') return;

                            const original = group.querySelector('line');
                            const edgeId = group.dataset.rsFlowEdge;

                            if (!original || !edgeId) return;

                            group.dataset.rsFlowHitReady = '1';

                            const hit = document.createElementNS(
                                'http://www.w3.org/2000/svg',
                                'path'
                            );
                            hit.setAttribute('fill', 'none');

                            hit.setAttribute('stroke', 'transparent');
                            hit.setAttribute('stroke-width', '24');
                            hit.setAttribute('pointer-events', 'stroke');
                            hit.style.pointerEvents = 'stroke';
                            hit.style.cursor = 'pointer';

                            function syncHit() {
                                for (const name of ['x1', 'y1', 'x2', 'y2']) {
                                    const value = original.getAttribute(name);
                                    if (value !== null) {
                                        hit.setAttribute(name, value);
                                    }
                                }

                                const route = original.getAttribute(
                                    'data-rs-route-v46'
                                );
                                if (route) {
                                    hit.setAttribute('d', route);
                                }
                                hit.style.visibility =
                                    original.style.visibility || '';
                            }

                            // Добавляем после оригинала: существующий
                            // querySelector('line') должен находить оригинал.
                            group.appendChild(hit);

                            const observer = new MutationObserver(syncHit);

                            observer.observe(original, {
                                attributes: true,
                                attributeFilter: [
                                    'x1', 'y1', 'x2', 'y2', 'style',
                                    'data-rs-route-v46'
                                ]
                            });

                            flowHitObserversV33.push(observer);
                            syncHit();

                            hit.addEventListener('click', event => {
                                if (event.shiftKey || spacePressed) return;

                                event.preventDefault();
                                event.stopPropagation();

                                canvas.dispatchEvent(new CustomEvent(
                                    'rs-edit-flow-v33',
                                    {detail: {edge_id: edgeId}}
                                ));
                            }, {signal});
                        });
                    }

                    attachFlowHitsV33();
                    setTimeout(attachFlowHitsV33, 100);
                    setTimeout(attachFlowHitsV33, 350);

                    signal.addEventListener('abort', () => {
                        flowHitObserversV33.forEach(
                            observer => observer.disconnect()
                        );
                    }, {once: true});

                    // RS_DIAGRAM_CHAIN_EDITOR_V32_MENU
                    // Контекстное меню для выделенных размещений.
                    const chainMenuV32 = document.createElement('div');

                    chainMenuV32.style.cssText = [
                        'position:absolute',
                        'z-index:100',
                        'display:none',
                        'padding:4px',
                        'background:#fff',
                        'border:1px solid #cbd5e1',
                        'border-radius:5px',
                        'box-shadow:0 4px 14px rgba(0,0,0,.25)'
                    ].join(';');

                    const chainButtonV32 = document.createElement('button');
                    chainButtonV32.type = 'button';
                    chainButtonV32.textContent = 'Создать связь…';
                    chainButtonV32.style.cssText = [
                        'border:0',
                        'background:transparent',
                        'padding:8px 12px',
                        'cursor:pointer',
                        'color:#0f172a',
                        'white-space:nowrap'
                    ].join(';');

                    chainMenuV32.appendChild(chainButtonV32);
                    viewport.appendChild(chainMenuV32);

                    // RS_DIAGRAM_RADIAL_MENU_V37
                    let pointerV37 = null;
                    let pointV37 = null;

                    const wheelV37 = document.createElement('div');
                    wheelV37.style.cssText = [
                        'position:absolute',
                        'width:440px',
                        'height:440px',
                        'display:none',
                        'z-index:120',
                        'border-radius:50%',
                        'background:rgba(15,23,42,.96)',
                        'border:1px solid #64748b',
                        'box-shadow:0 4px 18px rgba(0,0,0,.4)',
                        'box-sizing:border-box'
                    ].join(';');

                    function buttonV37(text, left, top) {
                        const button = document.createElement('button');
                        button.type = 'button';
                        button.textContent = text;
                        button.style.cssText = [
                            'position:absolute',
                            'left:' + left + 'px',
                            'top:' + top + 'px',
                            'width:76px',
                            'height:50px',
                            'border:1px solid #64748b',
                            'border-radius:10px',
                            'background:#273649',
                            'color:white',
                            'cursor:pointer',
                            'font-size:12px'
                        ].join(';');
                        wheelV37.appendChild(button);
                        return button;
                    }

                    const importV37 = buttonV37('Импорт', 182, 168);
                    const linkV37 = buttonV37('Связь', 182, 224);

                    // RS_BPMN_SYMBOLS_V39: кнопки по окружности.
                    const symbolsV39 = [
                        ['START_EVENT', 'Старт'],
                        ['INTERMEDIATE_EVENT', 'Событие'],
                        ['END_EVENT', 'Конец'],
                        ['TASK', 'Задача'],
                        ['SUBPROCESS', 'Подпроцесс'],
                        ['EXCLUSIVE_GATEWAY', 'ИЛИ'],
                        ['PARALLEL_GATEWAY', 'И'],
                        ['INCLUSIVE_GATEWAY', 'И/ИЛИ'],
                        ['PARTICIPANT', 'Участник'],
                        ['LANE', 'Дорожка'],
                        ['DATA_INPUT', 'Вход'],
                        ['DATA_OUTPUT', 'Выход'],
                        ['DATA_COLLECTION', 'Набор данных']
                    ];

                    symbolsV39.forEach((item, index) => {
                        const angle = -Math.PI / 2 +
                            index * 2 * Math.PI / symbolsV39.length;
                        const radius = 175;
                        const x = 220 + Math.cos(angle) * radius - 38;
                        const y = 220 + Math.sin(angle) * radius - 25;
                        const button = buttonV37(
                            item[1], Math.round(x), Math.round(y)
                        );

                        button.addEventListener('click', event => {
                            event.stopPropagation();
                            if (!pointV37) return;
                            const point = {...pointV37};
                            closeWheelV37();
                            canvas.dispatchEvent(new CustomEvent(
                                'rs-radial-symbol-v39',
                                {
                                    detail: {
                                        kind: item[0],
                                        x: point.x,
                                        y: point.y
                                    }
                                }
                            ));
                        }, {signal});
                    });


                    // RS_BPMN_WHEEL_VISUAL_V54
                    // Миниатюры задаются только встроенной разметкой.
                    // Названия кнопок берутся как текст, не как HTML.
                    const iconsV54 = {
                        START_EVENT:
                            '<circle cx="22" cy="18" r="13" ' +
                            'fill="#244b43" stroke="#86efac" stroke-width="2"/>',

                        INTERMEDIATE_EVENT:
                            '<circle cx="22" cy="18" r="13" ' +
                            'fill="#4a4123" stroke="#facc15" stroke-width="2"/>' +
                            '<circle cx="22" cy="18" r="10" ' +
                            'fill="none" stroke="#facc15" stroke-width="1.5"/>',

                        END_EVENT:
                            '<circle cx="22" cy="18" r="12" ' +
                            'fill="#512b35" stroke="#fb7185" stroke-width="4"/>',

                        TASK:
                            '<rect x="4" y="5" width="36" height="26" rx="5" ' +
                            'fill="#273649" stroke="#93c5fd" stroke-width="2"/>',

                        SUBPROCESS:
                            '<rect x="4" y="4" width="36" height="28" rx="5" ' +
                            'fill="#273649" stroke="#93c5fd" stroke-width="2"/>' +
                            '<rect x="18" y="21" width="8" height="8" ' +
                            'fill="none" stroke="#e2e8f0"/>' +
                            '<path d="M20 25h4 M22 23v4" ' +
                            'stroke="#e2e8f0" fill="none"/>',

                        EXCLUSIVE_GATEWAY:
                            '<path d="M22 2 L38 18 L22 34 L6 18 Z" ' +
                            'fill="#53472a" stroke="#facc15" stroke-width="2"/>' +
                            '<path d="M17 13 L27 23 M27 13 L17 23" ' +
                            'fill="none" stroke="#facc15" stroke-width="2"/>',

                        PARALLEL_GATEWAY:
                            '<path d="M22 2 L38 18 L22 34 L6 18 Z" ' +
                            'fill="#53472a" stroke="#facc15" stroke-width="2"/>' +
                            '<path d="M22 11v14 M15 18h14" ' +
                            'fill="none" stroke="#facc15" stroke-width="2"/>',

                        INCLUSIVE_GATEWAY:
                            '<path d="M22 2 L38 18 L22 34 L6 18 Z" ' +
                            'fill="#53472a" stroke="#facc15" stroke-width="2"/>' +
                            '<circle cx="22" cy="18" r="6" fill="none" ' +
                            'stroke="#facc15" stroke-width="2"/>',

                        PARTICIPANT:
                            '<rect x="3" y="5" width="38" height="26" ' +
                            'fill="#2d4161" stroke="#93c5fd" stroke-width="2"/>' +
                            '<path d="M15 5v26" stroke="#93c5fd"/>' +
                            '<circle cx="9" cy="13" r="3" fill="none" ' +
                            'stroke="#bfdbfe"/>' +
                            '<path d="M5 24c0-7 8-7 8 0" fill="none" ' +
                            'stroke="#bfdbfe"/>',

                        LANE:
                            '<rect x="3" y="5" width="38" height="26" ' +
                            'fill="none" stroke="#94a3b8" stroke-width="2"/>' +
                            '<path d="M12 5v26" stroke="#94a3b8"/>',

                        DATA_INPUT:
                            '<path d="M12 3 H27 L33 9 V33 H12 Z ' +
                            'M27 3 V9 H33" fill="#26394b" ' +
                            'stroke="#bfdbfe" stroke-width="1.5"/>' +
                            '<path d="M15 15 H22 V12 L27 17 L22 22 V19 H15 Z" ' +
                            'fill="none" stroke="#bfdbfe"/>',

                        DATA_OUTPUT:
                            '<path d="M12 3 H27 L33 9 V33 H12 Z ' +
                            'M27 3 V9 H33" fill="#26394b" ' +
                            'stroke="#bfdbfe" stroke-width="1.5"/>' +
                            '<path d="M15 15 H22 V12 L27 17 L22 22 V19 H15 Z" ' +
                            'fill="#bfdbfe" stroke="#bfdbfe"/>',

                        DATA_COLLECTION:
                            '<path d="M12 3 H27 L33 9 V33 H12 Z ' +
                            'M27 3 V9 H33" fill="#26394b" ' +
                            'stroke="#bfdbfe" stroke-width="1.5"/>' +
                            '<path d="M18 25v5 M22 25v5 M26 25v5" ' +
                            'stroke="#bfdbfe" stroke-width="1.5"/>'
                    };

                    // После создания кнопок их порядок совпадает с
                    // массивом symbolsV39: сначала Импорт и Связь,
                    // затем кнопки символов.
                    const symbolButtonsV54 = Array.from(
                        wheelV37.querySelectorAll('button')
                    ).slice(2);

                    symbolsV39.forEach((item, index) => {
                        const button = symbolButtonsV54[index];
                        const icon = iconsV54[item[0]];
                        if (!button || !icon) return;

                        const label = button.textContent;
                        button.textContent = '';
                        button.title = label;
                        button.setAttribute('aria-label', label);

                        button.style.display = 'flex';
                        button.style.flexDirection = 'column';
                        button.style.alignItems = 'center';
                        button.style.justifyContent = 'center';
                        button.style.gap = '1px';
                        button.style.padding = '2px';
                        button.style.fontSize = '10px';
                        button.style.lineHeight = '11px';

                        const picture = document.createElement('span');
                        picture.style.cssText = [
                            'display:block',
                            'width:44px',
                            'height:29px',
                            'pointer-events:none'
                        ].join(';');

                        picture.innerHTML =
                            '<svg xmlns="http://www.w3.org/2000/svg" ' +
                            'width="44" height="29" viewBox="0 0 44 36" ' +
                            'aria-hidden="true">' + icon + '</svg>';

                        const caption = document.createElement('span');
                        caption.textContent = label;
                        caption.style.cssText = [
                            'display:block',
                            'max-width:72px',
                            'max-height:22px',
                            'overflow:hidden',
                            'text-align:center',
                            'pointer-events:none'
                        ].join(';');

                        button.appendChild(picture);
                        button.appendChild(caption);
                    });


                    const captionV37 = document.createElement('div');
                    captionV37.textContent = 'V';
                    captionV37.style.cssText = [
                        'position:absolute',
                        'left:0',
                        'top:205px',
                        'width:100%',
                        'text-align:center',
                        'color:#94a3b8',
                        'font-size:16px',
                        'pointer-events:none'
                    ].join(';');
                    wheelV37.appendChild(captionV37);
                    viewport.appendChild(wheelV37);

                    function closeWheelV37() {
                        wheelV37.style.display = 'none';
                    }

                    viewport.addEventListener('pointermove', event => {
                        pointerV37 = {
                            x: event.clientX,
                            y: event.clientY
                        };
                    }, {signal});

                    // Capture отключает старый обработчик V34 только
                    // для V над этим полем.
                    document.addEventListener('keydown', event => {
                        if (
                            event.code !== 'KeyV' ||
                            event.repeat ||
                            event.ctrlKey ||
                            event.altKey ||
                            event.metaKey ||
                            editableTarget(event.target) ||
                            !viewport.matches(':hover') ||
                            !pointerV37
                        ) {
                            return;
                        }

                        event.preventDefault();
                        event.stopImmediatePropagation();

                        const canvasRect = canvas.getBoundingClientRect();
                        const viewportRect = viewport.getBoundingClientRect();
                        const scale = Number(shared.scale) || 1;

                        // Запоминаем координаты поля до открытия меню.
                        pointV37 = {
                            x: (pointerV37.x - canvasRect.left) / scale,
                            y: (pointerV37.y - canvasRect.top) / scale
                        };

                        const selected = Array.isArray(shared.selectedNodesV31)
                            ? shared.selectedNodesV31 : [];

                        linkV37.disabled = selected.length < 2;
                        linkV37.style.opacity = selected.length < 2
                            ? '0.45' : '1';
                        linkV37.title = selected.length < 2
                            ? 'Выделите минимум два объекта: Shift + ЛКМ'
                            : 'Создать связи';

                        // Убираем старое меню ПКМ/V, если оно открыто.
                        if (typeof hideChainMenuV32 === 'function') {
                            hideChainMenuV32();
                        }

                        const px = pointerV37.x - viewportRect.left;
                        const py = pointerV37.y - viewportRect.top;

                        // RS_BPMN_WHEEL_VISUAL_V54
                        // Не увеличиваем колесо, только уменьшаем
                        // при недостатке места.
                        const wheelScaleV54 = Math.min(
                            1,
                            Math.max(
                                0.1,
                                Math.min(
                                    viewportRect.width / 440,
                                    viewportRect.height / 440
                                )
                            )
                        );
                        const wheelSizeV54 = 440 * wheelScaleV54;
                        wheelV37.style.transformOrigin = 'top left';
                        wheelV37.style.transform =
                            'scale(' + wheelScaleV54 + ')';

                        const left = Math.max(
                            0, Math.min(
                                px - wheelSizeV54 / 2,
                                viewportRect.width - wheelSizeV54
                            )
                        );
                        const top = Math.max(
                            0, Math.min(py - wheelSizeV54 / 2, viewportRect.height - wheelSizeV54)
                        );

                        wheelV37.style.left = left + 'px';
                        wheelV37.style.top = top + 'px';
                        wheelV37.style.display = 'block';
                    }, {capture: true, signal});

                    importV37.addEventListener('click', event => {
                        event.stopPropagation();
                        if (!pointV37) return;
                        const point = {...pointV37};
                        closeWheelV37();
                        canvas.dispatchEvent(new CustomEvent(
                            'rs-radial-import-v37',
                            {detail: point}
                        ));
                    }, {signal});

                    linkV37.addEventListener('click', event => {
                        event.stopPropagation();

                        const selected = Array.isArray(shared.selectedNodesV31)
                            ? shared.selectedNodesV31.slice() : [];

                        if (selected.length < 2) return;

                        closeWheelV37();
                        canvas.dispatchEvent(new CustomEvent(
                            'rs-open-chain-v32',
                            {detail: {nodes: selected}}
                        ));
                    }, {signal});

                    document.addEventListener('pointerdown', event => {
                        if (
                            wheelV37.style.display !== 'none' &&
                            !wheelV37.contains(event.target)
                        ) {
                            closeWheelV37();
                        }
                    }, {capture: true, signal});

                    document.addEventListener('keydown', event => {
                        if (
                            event.key === 'Escape' &&
                            wheelV37.style.display !== 'none'
                        ) {
                            closeWheelV37();
                            event.preventDefault();
                            event.stopImmediatePropagation();
                        }
                    }, {capture: true, signal});

                    signal.addEventListener('abort', () => {
                        wheelV37.remove();
                    }, {once: true});


                    // RS_DIAGRAM_V_MENU_V34
                    // Последняя позиция курсора внутри рабочей области.
                    let lastPointerV34 = null;

                    viewport.addEventListener('pointermove', event => {
                        const rect = viewport.getBoundingClientRect();

                        lastPointerV34 = {
                            x: event.clientX - rect.left,
                            y: event.clientY - rect.top
                        };
                    }, {signal});

                    document.addEventListener('keydown', event => {
                        if (
                            event.code !== 'KeyV' ||
                            event.repeat ||
                            event.ctrlKey ||
                            event.altKey ||
                            event.metaKey ||
                            editableTarget(event.target) ||
                            !viewport.matches(':hover') ||
                            !lastPointerV34
                        ) {
                            return;
                        }

                        event.preventDefault();

                        const selected = shared.selectedNodesV31;
                        const count = Array.isArray(selected)
                            ? selected.length : 0;

                        // Используем ту же команду, что и меню ПКМ.
                        chainButtonV32.disabled = count < 2;
                        chainButtonV32.textContent = count < 2
                            ? 'Выделите минимум два объекта'
                            : 'Создать связь…';
                        chainButtonV32.style.opacity = count < 2 ? '0.55' : '1';
                        chainButtonV32.style.cursor = count < 2
                            ? 'default' : 'pointer';

                        chainMenuV32.style.display = 'block';

                        const rect = viewport.getBoundingClientRect();
                        const x = Math.max(
                            0,
                            Math.min(
                                lastPointerV34.x,
                                rect.width - chainMenuV32.offsetWidth
                            )
                        );
                        const y = Math.max(
                            0,
                            Math.min(
                                lastPointerV34.y,
                                rect.height - chainMenuV32.offsetHeight
                            )
                        );

                        chainMenuV32.style.left = x + 'px';
                        chainMenuV32.style.top = y + 'px';
                    }, {signal});

                    // При открытии меню через ПКМ восстанавливаем кнопку:
                    // V мог оставить её неактивной при малом выделении.
                    viewport.addEventListener('contextmenu', () => {
                        const selected = shared.selectedNodesV31;
                        if (Array.isArray(selected) && selected.length >= 2) {
                            chainButtonV32.disabled = false;
                            chainButtonV32.textContent = 'Создать связь…';
                            chainButtonV32.style.opacity = '1';
                            chainButtonV32.style.cursor = 'pointer';
                        }
                    }, {capture: true, signal});


                    function hideChainMenuV32() {
                        chainMenuV32.style.display = 'none';
                    }

                    viewport.addEventListener('contextmenu', event => {
                        const selected = shared.selectedNodesV31;

                        if (!Array.isArray(selected) || selected.length < 2) {
                            return;
                        }

                        event.preventDefault();

                        const rect = viewport.getBoundingClientRect();
                        chainMenuV32.style.display = 'block';

                        const x = Math.max(
                            0,
                            Math.min(
                                event.clientX - rect.left,
                                rect.width - chainMenuV32.offsetWidth
                            )
                        );

                        const y = Math.max(
                            0,
                            Math.min(
                                event.clientY - rect.top,
                                rect.height - chainMenuV32.offsetHeight
                            )
                        );

                        chainMenuV32.style.left = x + 'px';
                        chainMenuV32.style.top = y + 'px';
                    }, {signal});

                    chainButtonV32.addEventListener('click', event => {
                        event.stopPropagation();
                        hideChainMenuV32();

                        const selected = Array.isArray(
                            shared.selectedNodesV31
                        ) ? shared.selectedNodesV31.slice() : [];

                        canvas.dispatchEvent(new CustomEvent(
                            'rs-open-chain-v32',
                            {detail: {nodes: selected}}
                        ));
                    }, {signal});

                    document.addEventListener('pointerdown', event => {
                        if (!chainMenuV32.contains(event.target)) {
                            hideChainMenuV32();
                        }
                    }, {capture: true, signal});

                    document.addEventListener('keydown', event => {
                        if (event.key === 'Escape') {
                            hideChainMenuV32();
                        }
                    }, {signal});

                    signal.addEventListener('abort', () => {
                        chainMenuV32.remove();
                    }, {once: true});
                    // Порядок массива соответствует порядку выделения.
                    if (!Array.isArray(shared.selectedNodesV31)) {
                        shared.selectedNodesV31 = [];
                    }

                    const selectionInfo = document.createElement('div');
                    selectionInfo.style.cssText = [
                        'position:absolute',
                        'left:8px',
                        'bottom:8px',
                        'right:8px',
                        'max-height:48px',
                        'overflow:auto',
                        'white-space:normal',
                        'z-index:20',
                        'padding:5px 8px',
                        'border-radius:4px',
                        'background:rgba(15,23,42,.88)',
                        'color:#e2e8f0',
                        'font-size:12px',
                        'pointer-events:none'
                    ].join(';');

                    viewport.appendChild(selectionInfo);

                    function updateSelectionV31() {
                        const selected = shared.selectedNodesV31;

                        canvas.querySelectorAll('[data-rs-node]').forEach(
                            node => {
                                const id = node.dataset.rsNode;
                                const index = selected.indexOf(id);

                                // RS_DIAGRAM_PORT_CLICK_V47
                                let outlineV47 = node.querySelector(
                                    ':scope > [data-rs-selection-v47]'
                                );

                                if (!outlineV47) {
                                    outlineV47 = document.createElement('div');
                                    outlineV47.dataset.rsSelectionV47 = '1';
                                    outlineV47.style.cssText = [
                                        'position:absolute',
                                        'pointer-events:none',
                                        'z-index:4',
                                        'box-sizing:border-box',
                                        'display:none'
                                    ].join(';');
                                    node.appendChild(outlineV47);
                                }

                                node.style.outline = '';
                                node.style.outlineOffset = '';

                                if (index < 0) {
                                    outlineV47.style.display = 'none';
                                } else {
                                    outlineV47.style.display = 'block';

                                    const shape = node.dataset.rsShape;

                                    if (shape === 'circle') {
                                        outlineV47.style.left =
                                            'calc(50% - 32px)';
                                        outlineV47.style.top =
                                            'calc(50% - 32px)';
                                        outlineV47.style.width = '64px';
                                        outlineV47.style.height = '64px';
                                        outlineV47.style.borderRadius = '50%';
                                        outlineV47.style.transform = '';
                                    } else if (shape === 'diamond') {
                                        // Ромб V41 имеет диагональ 60 px.
                                        // Квадрат со стороной 46 px после
                                        // поворота окружает его с отступом.
                                        outlineV47.style.left =
                                            'calc(50% - 23px)';
                                        outlineV47.style.top =
                                            'calc(50% - 23px)';
                                        outlineV47.style.width = '46px';
                                        outlineV47.style.height = '46px';
                                        outlineV47.style.borderRadius = '0';
                                        outlineV47.style.transform =
                                            'rotate(45deg)';
                                    } else {
                                        outlineV47.style.left = '-3px';
                                        outlineV47.style.top = '-3px';
                                        outlineV47.style.width =
                                            'calc(100% + 6px)';
                                        outlineV47.style.height =
                                            'calc(100% + 6px)';
                                        outlineV47.style.borderRadius = '4px';
                                        outlineV47.style.transform = '';
                                    }

                                    outlineV47.style.border =
                                        '3px solid #38bdf8';
                                }
                            }
                        );

                        selectionInfo.textContent =
                            'Точка → точка — связь · Esc — отмена · ' +
                            'Shift + ЛКМ — выделить объекты · ' +
                            'Esc — снять выделение · ' +
                            'Выбрано: ' + selected.length;
                    }

                    // Capture не даёт обычному обработчику перетаскивания
                    // начать движение объекта при Shift + ЛКМ.
                    viewport.addEventListener('pointerdown', event => {
                        if (
                            event.button !== 0 ||
                            !event.shiftKey ||
                            spacePressed
                        ) {
                            return;
                        }

                        const target = event.target;
                        if (!(target instanceof Element)) return;

                        const node = target.closest('[data-rs-node]');
                        if (!node || !canvas.contains(node)) return;

                        const id = node.dataset.rsNode;
                        if (!id) return;

                        event.preventDefault();
                        event.stopImmediatePropagation();

                        const selected = shared.selectedNodesV31;
                        const index = selected.indexOf(id);

                        if (index >= 0) {
                            selected.splice(index, 1);
                        } else {
                            selected.push(id);
                        }

                        updateSelectionV31();
                    }, {capture: true, signal});

                    document.addEventListener('keydown', event => {
                        if (
                            event.key !== 'Escape' ||
                            editableTarget(event.target)
                        ) {
                            return;
                        }

                        if (shared.selectedNodesV31.length === 0) return;

                        shared.selectedNodesV31 = [];
                        updateSelectionV31();

                        event.preventDefault();
                        event.stopPropagation();
                    }, {capture: true, signal});

                    // При refresh V25 отменяет старый controller.
                    // Убираем подсказку предыдущего экземпляра.
                    signal.addEventListener('abort', () => {
                        selectionInfo.remove();
                    }, {once: true});

                    updateSelectionV31();
                    setTimeout(updateSelectionV31, 100);
                    setTimeout(updateSelectionV31, 350);

                    applyView();
                }

                attach();
            })();
            """.replace("CANVAS_ID", str(canvas.id))

            ui.run_javascript(pan_zoom_script)

            markup, line_count = render_smart_links_svg(
                state["nodes"],
                state["repository_links"],
                state["edges"],
                WIDTH,
                HEIGHT,
            )

            ui.html(markup, sanitize=False).style(
                "position:absolute; left:0; top:0; "
                "pointer-events:none; z-index:0;"
            )

            for node in state["nodes"]:
                node_id = node["id"]
                safe_node_id = smart_link_key(node_id)

                symbol_type_v39 = node.get("symbol_type")
                symbol_style_v39 = ""

                if symbol_type_v39 in {
                    "START_EVENT", "INTERMEDIATE_EVENT", "END_EVENT"
                }:
                    symbol_style_v39 = (
                        "border-radius:50%; background:#244b43; "
                    )
                    if symbol_type_v39 == "INTERMEDIATE_EVENT":
                        symbol_style_v39 += "border:4px double #86efac; "
                    elif symbol_type_v39 == "END_EVENT":
                        symbol_style_v39 += "border:5px solid #86efac; "
                    else:
                        symbol_style_v39 += "border:2px solid #86efac; "

                elif symbol_type_v39 in {
                    "EXCLUSIVE_GATEWAY",
                    "PARALLEL_GATEWAY",
                    "INCLUSIVE_GATEWAY",
                }:
                    symbol_style_v39 = (
                        "border-radius:0; border:2px solid #facc15; "
                        "background:#53472a; "
                    )

                elif symbol_type_v39 == "SUBPROCESS":
                    symbol_style_v39 = "border:2px solid #93c5fd; "

                elif symbol_type_v39 in {"PARTICIPANT", "LANE"}:
                    symbol_style_v39 = (
                        "border-radius:2px; border:2px solid #c4b5fd; "
                        "background:#35304b; "
                    )

                elif symbol_type_v39 == "TASK":
                    symbol_style_v39 = "border:2px solid #93c5fd; "

                with ui.element("div").style(
                    "position:absolute; "
                    f"left:{float(node['x'])}px; "
                    f"top:{float(node['y'])}px; "
                    f"width:{float(node.get('width', NODE_WIDTH))}px; "
                    f"height:{float(node.get('height', NODE_HEIGHT))}px; "
                    "box-sizing:border-box; border:2px solid #718096; "
                    "border-radius:9px; background:#273649; "
                    "color:white; padding:8px; cursor:grab; "
                    "touch-action:none; user-select:none; overflow:hidden;"
                    + symbol_style_v39
                ) as element:
                    if symbol_type_v39:
                        element.style(
                            "background:transparent; border:none; "
                            "padding:0; overflow:visible;"
                        )
                        markup_v45 = _bpmn_shape_markup_v41(
                            symbol_type_v39,
                            node.get("name", ""),
                        )
                        if symbol_type_v39 == "LANE":
                            lane_width_v45 = float(
                                node.get("width", NODE_WIDTH)
                            )
                            lane_height_v45 = float(
                                node.get("height", NODE_HEIGHT)
                            )
                            markup_v45 = markup_v45.replace(
                                'width="180" height="70" viewBox="0 0 180 70"',
                                (
                                    f'width="{lane_width_v45}" '
                                    f'height="{lane_height_v45}" '
                                    'viewBox="0 0 180 70" '
                                    'preserveAspectRatio="none"'
                                ),
                                1,
                            )
                        if symbol_type_v39 == "LANE":
                            markup_v45 = _bpmn_shape_markup_v41(
                                symbol_type_v39,
                                node.get("name", ""),
                            )
                        ui.html(
                            markup_v45,
                            sanitize=False,
                        ).style(
                            ('position:absolute; left:0; top:0; pointer-events:none; ' + f"width:{float(node.get('width', NODE_WIDTH))}px; " + f"height:{float(node.get('height', NODE_HEIGHT))}px;") if symbol_type_v39 == 'LANE' else 'position:absolute; left:0; top:0; width:180px; height:70px; pointer-events:none;'
                        )
                    else:
                        ui.label(node.get("name", "Объект")).style(
                            "font-size:14px; line-height:18px; "
                            "overflow:hidden; overflow-wrap:anywhere;"
                        )

                element.props(f'data-rs-node="{safe_node_id}"')
                if symbol_type_v39 == "LANE":
                    element.props('data-rs-lane-v49="1"')
                    element.on(
                        "rs-resize-lane-v49",
                        lambda e, n=node_id: resize_lane_v49(n, e),
                        args=["detail"],
                    )
                # RS_BPMN_VISUAL_FIX_V42: переименование двойным щелчком.
                if symbol_type_v39:
                    def rename_from_canvas_v42(e, n=node_id):
                        state["selected_node"] = n
                        rename_symbol_v39()

                    element.on("dblclick", rename_from_canvas_v42)
                if symbol_type_v39 in {
                    "START_EVENT", "INTERMEDIATE_EVENT", "END_EVENT"
                }:
                    element.props('data-rs-shape="circle"')
                elif symbol_type_v39 in {
                    "EXCLUSIVE_GATEWAY",
                    "PARALLEL_GATEWAY",
                    "INCLUSIVE_GATEWAY",
                }:
                    element.props('data-rs-shape="diamond"')
                element.style("z-index:1;")

                element.on(
                    "rs-canvas-moved",
                    lambda e, n=node_id: on_move(n, e),
                    args=["detail"],
                )

                # В JS передаётся только числовой ID компонента.
                # Пользовательский текст в код JS не вставляется.
                script = """
                (() => {
                    const componentId = 'cCOMPONENT_ID';
                    const canvasId = 'cCANVAS_ID';
                    let attempts = 0;

                    function updateLines() {
                        const canvas = document.getElementById(canvasId);
                        if (!canvas) return;

                        const nodes = new Map();

                        canvas.querySelectorAll('[data-rs-node]').forEach(el => {
                            nodes.set(el.dataset.rsNode, el);
                        });

                        canvas.querySelectorAll('.rs-smart-line').forEach(group => {
                            let source = nodes.get(group.dataset.source);
                            let target = nodes.get(group.dataset.target);
                            const line = group.querySelector('line');
                            const label = group.querySelector('text');

                            if (!source || !target || !line || !label) return;

                            // RS_DIAGRAM_DIRECTION_FREE_V36: исходное направление связи репозитория.
                            const sx = parseFloat(source.style.left) || 0;
                            const sy = parseFloat(source.style.top) || 0;
                            const tx = parseFloat(target.style.left) || 0;
                            const ty = parseFloat(target.style.top) || 0;

                            const sw = source.offsetWidth || 180;
                            const sh = source.offsetHeight || 70;
                            const tw = target.offsetWidth || 180;
                            const th = target.offsetHeight || 70;

                            const ax = sx + sw / 2;
                            const ay = sy + sh / 2;
                            const bx = tx + tw / 2;
                            const by = ty + th / 2;

                            let dx = bx - ax;
                            let dy = by - ay;
                            let distance = Math.hypot(dx, dy);

                            if (distance < 0.001) {
                                line.style.visibility = 'hidden';
                                label.style.visibility = 'hidden';
                                return;
                            }

                            line.style.visibility = '';
                            label.style.visibility = '';

                            const ux = dx / distance;
                            const uy = dy / distance;


                            // RS_DIAGRAM_ORTHOGONAL_V46
                            // Четыре точки: сверху, справа, снизу, слева.
                            function sidePoint(element, x, y, w, h, side) {
                                const shape = element.dataset.rsShape;
                                const cx = x + w / 2;
                                const cy = y + h / 2;

                                // В V41 круг и ромб находятся в центре
                                // прямоугольника элемента 180 x 70.
                                let rx = w / 2;
                                let ry = h / 2;

                                if (shape === 'circle') {
                                    rx = 29;
                                    ry = 29;
                                } else if (shape === 'diamond') {
                                    rx = 30;
                                    ry = 30;
                                }

                                if (side === 'left') {
                                    return {x: cx - rx, y: cy};
                                }
                                if (side === 'right') {
                                    return {x: cx + rx, y: cy};
                                }
                                if (side === 'top') {
                                    return {x: cx, y: cy - ry};
                                }
                                return {x: cx, y: cy + ry};
                            }

                            // RS_DIAGRAM_ROUTE_V50
                            // Выбираем стороны по промежуткам между
                            // видимыми границами, а не только центрами.
                            function boundsV50(element, x, y, w, h) {
                                const shape = element.dataset.rsShape;
                                const cx = x + w / 2;
                                const cy = y + h / 2;
                                let rx = w / 2;
                                let ry = h / 2;

                                if (shape === 'circle') {
                                    rx = 29;
                                    ry = 29;
                                } else if (shape === 'diamond') {
                                    rx = 30;
                                    ry = 30;
                                }

                                return {
                                    left: cx - rx,
                                    right: cx + rx,
                                    top: cy - ry,
                                    bottom: cy + ry
                                };
                            }

                            const sbV50 = boundsV50(
                                source, sx, sy, sw, sh
                            );
                            const tbV50 = boundsV50(
                                target, tx, ty, tw, th
                            );

                            const gapRightV50 = tbV50.left - sbV50.right;
                            const gapLeftV50 = sbV50.left - tbV50.right;
                            const gapDownV50 = tbV50.top - sbV50.bottom;
                            const gapUpV50 = sbV50.top - tbV50.bottom;

                            const candidatesV50 = [
                                {
                                    gap: gapRightV50,
                                    source: 'right',
                                    target: 'left'
                                },
                                {
                                    gap: gapLeftV50,
                                    source: 'left',
                                    target: 'right'
                                },
                                {
                                    gap: gapDownV50,
                                    source: 'bottom',
                                    target: 'top'
                                },
                                {
                                    gap: gapUpV50,
                                    source: 'top',
                                    target: 'bottom'
                                }
                            ];

                            // Предпочитаем направление с положительным
                            // просветом. При пересечении границ выбираем
                            // наименее перекрывающееся направление.
                            candidatesV50.sort((a, b) => b.gap - a.gap);
                            const chosenV50 = candidatesV50[0];
                            const sourceSide = chosenV50.source;
                            const targetSide = chosenV50.target;

                            const p1 = sidePoint(
                                source, sx, sy, sw, sh, sourceSide
                            );
                            const p2 = sidePoint(
                                target, tx, ty, tw, th, targetSide
                            );

                            line.setAttribute('x1', p1.x);
                            line.setAttribute('y1', p1.y);
                            line.setAttribute('x2', p2.x);
                            line.setAttribute('y2', p2.y);

                            const offset = parseFloat(
                                group.dataset.offset
                            ) || 0;

                            const vectorsV50 = {
                                left:   {x: -1, y: 0},
                                right:  {x:  1, y: 0},
                                top:    {x: 0, y: -1},
                                bottom: {x: 0, y:  1}
                            };

                            const svV50 = vectorsV50[sourceSide];
                            const tvV50 = vectorsV50[targetSide];

                            // Начальный и конечный прямые участки:
                            // стрелка входит в точку подключения снаружи.
                            // RS_DIAGRAM_ROUTE_GAP_V51
                            // При небольшом промежутке не допускаем,
                            // чтобы начальный и конечный отступы
                            // пересекались и линия возвращалась назад.
                            const clearanceV50 = chosenV50.gap > 0
                                ? Math.min(24, chosenV50.gap / 3)
                                : 24;
                            const aV50 = {
                                x: p1.x + svV50.x * clearanceV50,
                                y: p1.y + svV50.y * clearanceV50
                            };
                            const bV50 = {
                                x: p2.x + tvV50.x * clearanceV50,
                                y: p2.y + tvV50.y * clearanceV50
                            };

                            const pointsV50 = [p1, aV50];
                            let labelX;
                            let labelY;

                            if (
                                sourceSide === 'left' ||
                                sourceSide === 'right'
                            ) {
                                let middle = (aV50.x + bV50.x) / 2
                                    + offset;

                                if (chosenV50.gap > 0) {
                                    middle = Math.max(
                                        Math.min(aV50.x, bV50.x),
                                        Math.min(
                                            Math.max(aV50.x, bV50.x),
                                            middle
                                        )
                                    );
                                }
                                pointsV50.push(
                                    {x: middle, y: aV50.y},
                                    {x: middle, y: bV50.y}
                                );
                                labelX = middle;
                                labelY = (aV50.y + bV50.y) / 2 - 5;
                            } else {
                                let middle = (aV50.y + bV50.y) / 2
                                    + offset;

                                if (chosenV50.gap > 0) {
                                    middle = Math.max(
                                        Math.min(aV50.y, bV50.y),
                                        Math.min(
                                            Math.max(aV50.y, bV50.y),
                                            middle
                                        )
                                    );
                                }
                                pointsV50.push(
                                    {x: aV50.x, y: middle},
                                    {x: bV50.x, y: middle}
                                );
                                labelX = (aV50.x + bV50.x) / 2;
                                labelY = middle - 5;
                            }

                            pointsV50.push(bV50, p2);

                            // Убираем соседние совпадающие точки, но
                            // сохраняем последний участок для маркера.
                            const compactV50 = [];
                            for (const point of pointsV50) {
                                const previous = compactV50[
                                    compactV50.length - 1
                                ];
                                if (
                                    !previous ||
                                    previous.x !== point.x ||
                                    previous.y !== point.y
                                ) {
                                    compactV50.push(point);
                                }
                            }

                            const d = compactV50.map((point, index) =>
                                `${index === 0 ? 'M' : 'L'} ` +
                                `${point.x} ${point.y}`
                            ).join(' ');
                            let route = group.querySelector(
                                'path[data-rs-route-v46]'
                            );

                            if (!route) {
                                route = document.createElementNS(
                                    'http://www.w3.org/2000/svg',
                                    'path'
                                );
                                route.dataset.rsRouteV46 = '1';
                                route.setAttribute('fill', 'none');
                                route.setAttribute('pointer-events', 'none');

                                // Ставим видимую линию перед текстом и
                                // широкой областью нажатия.
                                group.insertBefore(route, label);
                            }

                            for (const attr of [
                                'stroke',
                                'stroke-width',
                                'stroke-dasharray',
                                'marker-start',
                                'marker-end'
                            ]) {
                                const value = line.getAttribute(attr);
                                if (value === null) {
                                    route.removeAttribute(attr);
                                } else {
                                    route.setAttribute(attr, value);
                                }
                            }

                            route.setAttribute('d', d);
                            route.style.visibility = line.style.visibility;
                            line.style.opacity = '0';

                            // Область нажатия V33 следит за этим атрибутом.
                            line.setAttribute('data-rs-route-v46', d);

                            label.setAttribute('x', labelX);
                            label.setAttribute('y', labelY);
                        });
                    }

                    function attach() {
                        const el = document.getElementById(componentId);

                        if (!el) {
                            attempts += 1;
                            if (attempts < 50) setTimeout(attach, 50);
                            return;
                        }

                        if (el.dataset.rsDragReady === '1') return;
                        el.dataset.rsDragReady = '1';

                        // RS_BPMN_LANE_WHEEL_V49
                        if (el.dataset.rsLaneV49 === '1') {
                            // Прозрачная внутренняя область пропускает
                            // события мыши к объектам и линиям под ней.
                            el.style.pointerEvents = 'none';

                            const laneHtml = el.querySelector(
                                '[data-rs-lane-frame-v49]'
                            );

                            if (laneHtml && laneHtml.parentElement) {
                                // ui.html V41 имел фиксированный размер
                                // 180 x 70. Дорожке нужен размер элемента.
                                laneHtml.parentElement.style.width = '100%';
                                laneHtml.parentElement.style.height = '100%';
                            }

                            function makeDragArea(css) {
                                const area = document.createElement('div');
                                area.style.cssText = [
                                    'position:absolute',
                                    'pointer-events:auto',
                                    'z-index:6',
                                    'cursor:grab',
                                    css
                                ].join(';');
                                el.appendChild(area);
                                return area;
                            }

                            // Дорожку можно перетаскивать за шапку
                            // и границы, не перекрывая внутренность.
                            makeDragArea(
                                'left:0;top:0;width:34px;height:100%'
                            );
                            makeDragArea(
                                'left:0;top:0;width:100%;height:8px'
                            );
                            makeDragArea(
                                'left:0;bottom:0;width:100%;height:8px'
                            );
                            makeDragArea(
                                'right:0;top:0;width:8px;height:100%'
                            );

                            const handle = document.createElement('div');
                            handle.title = 'Потяните для изменения размера';
                            handle.style.cssText = [
                                'position:absolute',
                                'right:-5px',
                                'bottom:-5px',
                                'width:14px',
                                'height:14px',
                                'background:#38bdf8',
                                'border:2px solid #e0f2fe',
                                'box-sizing:border-box',
                                'pointer-events:auto',
                                'cursor:nwse-resize',
                                'z-index:9'
                            ].join(';');

                            el.appendChild(handle);

                            let resizing = false;
                            let resizePointer = null;
                            let startX = 0;
                            let startY = 0;
                            let startWidth = 0;
                            let startHeight = 0;

                            handle.addEventListener('pointerdown', event => {
                                if (event.button !== 0) return;

                                event.preventDefault();
                                event.stopPropagation();

                                resizing = true;
                                resizePointer = event.pointerId;
                                startX = event.clientX;
                                startY = event.clientY;
                                startWidth = el.offsetWidth;
                                startHeight = el.offsetHeight;

                                try {
                                    handle.setPointerCapture(event.pointerId);
                                } catch (_) {}
                            });

                            handle.addEventListener('pointermove', event => {
                                if (
                                    !resizing ||
                                    event.pointerId !== resizePointer
                                ) {
                                    return;
                                }

                                event.preventDefault();
                                event.stopPropagation();

                                const canvas = document.getElementById(canvasId);
                                if (!canvas) return;

                                const scale = parseFloat(
                                    canvas.dataset.rsViewScale
                                ) || 1;

                                const left = parseFloat(el.style.left) || 0;
                                const top = parseFloat(el.style.top) || 0;

                                const width = Math.max(
                                    100,
                                    Math.min(
                                        20000 - left,
                                        startWidth +
                                            (event.clientX - startX) / scale
                                    )
                                );

                                const height = Math.max(
                                    70,
                                    Math.min(
                                        20000 - top,
                                        startHeight +
                                            (event.clientY - startY) / scale
                                    )
                                );

                                el.style.width = width + 'px';
                                el.style.height = height + 'px';

                                // Обновляем линии во время изменения размера.
                                updateLines();
                            });

                            function finishResize(event) {
                                if (
                                    !resizing ||
                                    event.pointerId !== resizePointer
                                ) {
                                    return;
                                }

                                event.preventDefault();
                                event.stopPropagation();

                                resizing = false;
                                resizePointer = null;

                                el.dispatchEvent(new CustomEvent(
                                    'rs-resize-lane-v49',
                                    {
                                        detail: {
                                            width: parseFloat(el.style.width),
                                            height: parseFloat(el.style.height)
                                        }
                                    }
                                ));
                            }

                            handle.addEventListener('pointerup', finishResize);
                            handle.addEventListener('pointercancel', finishResize);
                        }

                        // RS_DIAGRAM_ORTHOGONAL_V46: точки подключения.
                        const pointLayerV46 = document.createElement('div');
                        pointLayerV46.style.cssText = [
                            'position:absolute',
                            'inset:0',
                            'pointer-events:none',
                            'z-index:5',
                            'opacity:0'
                        ].join(';');

                        const shapeV46 = el.dataset.rsShape;
                        const positionsV46 = shapeV46 === 'circle'
                            ? [
                                ['50%', 'calc(50% - 29px)'],
                                ['calc(50% + 29px)', '50%'],
                                ['50%', 'calc(50% + 29px)'],
                                ['calc(50% - 29px)', '50%']
                            ]
                            : shapeV46 === 'diamond'
                            ? [
                                ['50%', 'calc(50% - 30px)'],
                                ['calc(50% + 30px)', '50%'],
                                ['50%', 'calc(50% + 30px)'],
                                ['calc(50% - 30px)', '50%']
                            ]
                            : [
                                ['50%', '0'],
                                ['100%', '50%'],
                                ['50%', '100%'],
                                ['0', '50%']
                            ];

                        positionsV46.forEach(position => {
                            const dot = document.createElement('span');
                            dot.style.cssText = [
                                'position:absolute',
                                'left:' + position[0],
                                'top:' + position[1],
                                'width:12px',
                                'height:12px',
                                'transform:translate(-50%,-50%)',
                                'border-radius:50%',
                                'background:#38bdf8',
                                'border:2px solid #e0f2fe',
                                'box-sizing:border-box',
                                'pointer-events:auto',
                                'cursor:crosshair'
                            ].join(';');

                            dot.title =
                                'Нажмите начальную точку, затем конечную. ' +
                                'Esc — отмена.';

                            // Не запускаем перетаскивание элемента.
                            dot.addEventListener('pointerdown', event => {
                                if (event.button !== 0) return;
                                event.preventDefault();
                                event.stopPropagation();
                            });

                            dot.addEventListener('click', event => {
                                if (event.button !== 0) return;
                                event.preventDefault();
                                event.stopPropagation();

                                // Этот обработчик работает в отдельной
                                // функции JS, поэтому ищем своё полотно
                                // по ID, а не используем чужие переменные.
                                const ownCanvasV47 =
                                    document.getElementById(canvasId);
                                if (!ownCanvasV47) return;

                                const nodeId = el.dataset.rsNode;
                                if (!nodeId) return;

                                const start =
                                    ownCanvasV47.dataset.rsPortStartV47;

                                if (!start) {
                                    ownCanvasV47.dataset.rsPortStartV47 =
                                        nodeId;

                                    if (ownCanvasV47.parentElement) {
                                        ownCanvasV47.parentElement.style.cursor =
                                            'crosshair';
                                    }
                                    return;
                                }

                                delete ownCanvasV47.dataset.rsPortStartV47;

                                if (ownCanvasV47.parentElement) {
                                    ownCanvasV47.parentElement.style.cursor = '';
                                }

                                // Повторное нажатие на тот же элемент
                                // отменяет начатое соединение.
                                if (start === nodeId) return;

                                ownCanvasV47.dispatchEvent(new CustomEvent(
                                    'rs-open-chain-v32',
                                    {
                                        detail: {
                                            nodes: [start, nodeId]
                                        }
                                    }
                                ));
                            });

                            pointLayerV46.appendChild(dot);
                        });

                        el.appendChild(pointLayerV46);
                        el.addEventListener('pointerenter', () => {
                            pointLayerV46.style.opacity = '1';
                        });
                        el.addEventListener('pointerleave', () => {
                            pointLayerV46.style.opacity = '0';
                        });

                        let active = false;
                        let startX = 0;
                        let startY = 0;
                        let left = 0;
                        let top = 0;

                        el.addEventListener('pointerdown', e => {
                            if (e.button !== 0) return;
                            active = true;
                            startX = e.clientX;
                            startY = e.clientY;
                            left = parseFloat(el.style.left) || 0;
                            top = parseFloat(el.style.top) || 0;
                            el.setPointerCapture(e.pointerId);
                            el.style.cursor = 'grabbing';
                        });

                        el.addEventListener('pointermove', e => {
                            if (!active) return;

                            const x = Math.max(
                                0, Math.min(20000 - el.offsetWidth, left + (e.clientX - startX) / (parseFloat(document.getElementById(canvasId)?.dataset.rsViewScale) || 1))
                            );
                            const y = Math.max(
                                0, Math.min(20000 - el.offsetHeight, top + (e.clientY - startY) / (parseFloat(document.getElementById(canvasId)?.dataset.rsViewScale) || 1))
                            );

                            el.style.left = x + 'px';
                            el.style.top = y + 'px';
                            updateLines();
                        });

                        function finish() {
                            if (!active) return;
                            active = false;
                            el.style.cursor = 'grab';

                            el.dispatchEvent(new CustomEvent(
                                'rs-canvas-moved',
                                {
                                    detail: {
                                        x: parseFloat(el.style.left) || 0,
                                        y: parseFloat(el.style.top) || 0
                                    }
                                }
                            ));
                        }

                        el.addEventListener('pointerup', finish);
                        el.addEventListener('pointercancel', finish);
                    }

                    attach();
                    setTimeout(updateLines, 50);
                    setTimeout(updateLines, 250);
                })();
                """.replace(
                    "COMPONENT_ID", str(element.id)
                ).replace(
                    "CANVAS_ID", str(canvas.id)
                )

                ui.run_javascript(script)

    def add_node():
        object_id = state["selected_object"]

        if not object_id or object_id not in state["objects"]:
            ui.notify("Выберите объект репозитория.", type="warning")
            return

        if len(state["nodes"]) >= 500:
            ui.notify("Достигнут предел элементов.", type="warning")
            return

        index = len(state["nodes"])

        node = {
            "id": uuid.uuid4().hex,
            "object_id": object_id,
            "name": state["objects"][object_id],
            "x": 20 + (index % 4) * 210,
            "y": 20 + ((index // 4) % 5) * 90,
            "width": NODE_WIDTH,
            "height": NODE_HEIGHT,
        }

        state["nodes"].append(node)
        state["selected_node"] = node["id"]
        mark_dirty()
        update_node_selector()
        selector.value = node["id"]
        selector.update()
        draw_canvas.refresh()


    # RS_DIAGRAM_FLOW_TYPES_V29
    flow_state = {
        "source": None,
        "target": None,
        "kind": "CONTROL",
    }

    def create_flow_v29():
        source_id = flow_state["source"]
        target_id = flow_state["target"]
        kind = flow_state["kind"]

        allowed = {
            "MESSAGE",
            "CONTROL",
            "DEFAULT",
            "CONDITIONAL",
        }

        if kind not in allowed:
            ui.notify("Выберите вид потока.", type="warning")
            return

        node_ids = {str(node["id"]) for node in state["nodes"]}

        if source_id not in node_ids or target_id not in node_ids:
            ui.notify("Выберите начало и конец потока.", type="warning")
            return

        if source_id == target_id:
            ui.notify(
                "Начало и конец должны быть разными элементами.",
                type="warning",
            )
            return

        if len(state["edges"]) >= 2000:
            ui.notify("Достигнут предел линий.", type="warning")
            return

        state["edges"].append({
            "id": uuid.uuid4().hex,
            "source_node_id": source_id,
            "target_node_id": target_id,
            "label": "__RS_FLOW_V29__:" + kind,
        })

        mark_dirty()
        draw_canvas.refresh()
        ui.notify(
            "Поток добавлен. Сохраните диаграмму.",
            type="positive",
        )

    def remove_node():
        node_id = state["selected_node"]

        if not node_id:
            ui.notify(
                "Выберите элемент в списке удаления.",
                type="warning",
            )
            return

        connected = [
            edge for edge in state["edges"]
            if edge["source_node_id"] == node_id
            or edge["target_node_id"] == node_id
        ]

        if connected:
            ui.notify(
                "К элементу подключены линии. В V16 их нельзя "
                "редактировать, поэтому удаление элемента отменено.",
                type="warning",
                timeout=10000,
            )
            return

        state["nodes"] = [
            node for node in state["nodes"]
            if node["id"] != node_id
        ]
        state["selected_node"] = None
        mark_dirty()
        update_node_selector()
        draw_canvas.refresh()

    async def save():
        if state["saving"]:
            return

        state["saving"] = True
        save_button.disable()

        try:
            revision = await save_diagram(
                database_id,
                model_id,
                state["revision"],
                state["nodes"],
                state["edges"],
            )

            state["revision"] = revision
            state["dirty"] = False
            status.set_text(f"Сохранено в базе. Версия: {revision}")
            ui.notify("Модель сохранена.", type="positive")

        except DiagramConflict as exc:
            ui.notify(
                _message(exc),
                type="negative",
                timeout=12000,
            )

        except Exception as exc:
            ui.notify(
                "Сохранение не выполнено: " + _message(exc),
                type="negative",
                timeout=12000,
            )

        finally:
            state["saving"] = False
            save_button.enable()

    def request_close():
        if state["saving"]:
            ui.notify("Дождитесь окончания сохранения.", type="warning")
            return

        if not state["dirty"]:
            dialog.close()
            return

        with ui.dialog() as confirm, ui.card():
            ui.label("Есть несохранённые изменения. Закрыть редактор?")

            with ui.row():
                ui.button(
                    "Продолжить работу",
                    on_click=confirm.close,
                ).props("flat")

                def discard():
                    confirm.close()
                    dialog.close()

                ui.button(
                    "Закрыть без сохранения",
                    on_click=discard,
                    color="negative",
                )

        confirm.open()

    # RS_DIAGRAM_WORKBENCH_V27
    with ui.dialog() as dialog, ui.card().style(
        "width:100vw; max-width:100vw; "
        "height:100vh; max-height:100vh; "
        "padding:0; gap:0; overflow:hidden; "
        "display:flex; flex-direction:column; "
        "box-sizing:border-box; border-radius:0;"
    ):
        dialog.props("persistent maximized")

        # Верхняя панель проходит по всей ширине.
        with ui.element("div").style(
            "width:100%; height:7vh; min-height:52px; "
            "flex:none; display:flex; align-items:center; "
            "gap:12px; padding:6px 12px; "
            "box-sizing:border-box; "
            "border-bottom:1px solid #d7dee8; "
            "overflow:auto;"
        ):
            ui.label(f"{database_name} — {model_name}").style(
                "font-size:18px; font-weight:600; "
                "min-width:120px; flex:1; "
                "overflow:hidden; text-overflow:ellipsis;"
            )

            status = ui.label(
                f"Загружено из базы. Версия: {state['revision']}"
            ).style(
                "font-size:12px; color:#64748b; "
                "white-space:nowrap;"
            )

            save_button = ui.button(
                "Сохранить",
                on_click=save,
                icon="save",
                color="primary",
            ).props("dense")

            ui.button(
                "Закрыть",
                on_click=request_close,
            ).props("flat dense")

        # Нижняя часть: боковая панель и рабочая область.
        with ui.element("div").style(
            "display:flex; flex:1; min-height:0; "
            "width:100%; overflow:hidden;"
        ):
            with ui.element("div").style(
                "width:13%; min-width:180px; max-width:320px; "
                "flex:none; min-height:0; overflow:auto; "
                "padding:12px; box-sizing:border-box; "
                "border-right:1px solid #d7dee8; "
                "display:flex; flex-direction:column; gap:10px;"
            ):
                ui.label("Объекты").style(
                    "font-size:16px; font-weight:600;"
                )

                ui.label(
                    "Импорт из репозитория"
                ).style("font-size:12px; color:#64748b;")

                ui.select(
                    options=object_options,
                    label="Объект",
                    on_change=lambda e: state.update(
                        {"selected_object": e.value}
                    ),
                ).classes("w-full")

                ui.button(
                    "Добавить",
                    on_click=add_node,
                    icon="add",
                ).classes("w-full")

                ui.separator()

                # RS_BPMN_PALETTE_V55
                # Палитра символов BPMN: см. render_bpmn_palette_v55.
                render_bpmn_palette_v55(
                    add_symbol_v39,
                    on_event_pick=lambda kind: _insert_event_v58(
                        kind, add_symbol_v39
                    ),
                )

                ui.label("Размещения").style(
                    "font-size:14px; font-weight:600;"
                )

                selector = ui.select(
                    options=node_options(),
                    label="Элемент для удаления",
                    on_change=lambda e: state.update(
                        {"selected_node": e.value}
                    ),
                ).classes("w-full")

                ui.button(
                    "Удалить с поля",
                    on_click=remove_node,
                    icon="delete_outline",
                ).props("outline").classes("w-full")

                ui.label(
                    "Удаление размещения не удаляет объект "
                    "или его связи из репозитория."
                ).style("font-size:12px; color:#64748b;")

                ui.separator()


                # RS_DIAGRAM_FLOW_TYPES_V29_PANEL
                ui.separator()

                ui.label("Потоки").style(
                    "font-size:14px; font-weight:600;"
                )

                flow_source_selector = ui.select(
                    options=node_options(),
                    label="Начало",
                    on_change=lambda e: flow_state.update(
                        {"source": e.value}
                    ),
                ).classes("w-full")

                flow_target_selector = ui.select(
                    options=node_options(),
                    label="Конец",
                    on_change=lambda e: flow_state.update(
                        {"target": e.value}
                    ),
                ).classes("w-full")

                ui.select(
                    options={
                        "MESSAGE": "Поток сообщений",
                        "CONTROL": "Поток управления",
                        "DEFAULT": (
                            "Поток управления: в остальных случаях"
                        ),
                        "CONDITIONAL": (
                            "Условный поток управления"
                        ),
                    },
                    value="CONTROL",
                    label="Вид потока",
                    on_change=lambda e: flow_state.update(
                        {"kind": e.value}
                    ),
                ).classes("w-full")

                ui.button(
                    "Добавить поток",
                    icon="arrow_forward",
                    on_click=create_flow_v29,
                ).props("outline").classes("w-full")

                ui.label(
                    "Выберите начало и конец потока. "
                    "Поток сохраняется вместе с диаграммой."
                ).style("font-size:12px; color:#64748b;")

                ui.separator()
                ui.label("Символы BPMN").style(
                    "font-size:14px; font-weight:600;"
                )
                ui.select(
                    options=SYMBOLS_V39,
                    value="TASK",
                    label="Символ",
                    on_change=lambda e: symbol_choice_v39.update(
                        {"kind": e.value}
                    ),
                ).classes("w-full")
                ui.button(
                    "Добавить символ",
                    icon="add",
                    on_click=lambda: add_symbol_v39(
                        symbol_choice_v39["kind"]
                    ),
                ).classes("w-full")
                ui.button(
                    "Переименовать выбранный",
                    icon="edit",
                    on_click=rename_symbol_v39,
                ).props("outline").classes("w-full").style("min-height:52px; height:auto; white-space:normal; line-height:1.2;")
                ui.label(
                    "Для переименования выберите символ "
                    "в списке «Элемент для удаления». "
                    "Клавиша V открывает колесо символов."
                ).style("font-size:12px; color:#64748b;")

            with ui.element("div").style(
                "flex:1; min-width:0; min-height:0; "
                "display:flex; flex-direction:column; "
                "overflow:hidden;"
            ):
                ui.label(
                    "Пробел + перетаскивание — перемещение поля · "
                    "Колесо мыши — масштаб · "
                    "Перетаскивание объекта — перемещение объекта"
                ).style(
                    "flex:none; padding:5px 10px; "
                    "font-size:12px; color:#64748b; "
                    "border-bottom:1px solid #e2e8f0;"
                )

                # V25 подключает обработчики к родителю canvas.
                # Этот элемент должен оставаться непосредственным
                # родителем draw_canvas().
                with ui.element("div").style(
                    "flex:1; min-width:0; min-height:0; "
                    "width:100%; overflow:hidden;"
                ):
                    draw_canvas()

                if state["edges"]:
                    ui.label(
                        "Жёлтые пунктирные линии V14 сохранены отдельно "
                        "и пока не редактируются."
                    ).style(
                        "flex:none; padding:4px 10px; "
                        "font-size:12px; color:#a16207;"
                    )

    dialog.open()
