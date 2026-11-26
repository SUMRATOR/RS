# RS_DIAGRAM_SMART_LINKS_V23
"""
Визуальное представление связей на экспериментальном полотне.

Связи репозитория не копируются в rs_diagram_edges.
Существующие линии V14 показываются отдельно.
"""

from __future__ import annotations
# RS_BPMN_SYMBOLS_V39

import html
import math
import uuid


LINK_NAMES = {
    "USES": "Использует",
    "RESPONSIBLE_FOR": "Отвечает за",
    "GENERATES": "Создаёт",
    "MITIGATES": "Снижает",
    "SUPPORTS": "Поддерживает",
}


def key(value):
    """Привести UUID к единому безопасному виду."""
    return uuid.UUID(str(value)).hex


def _number(value):
    result = float(value)

    if not math.isfinite(result):
        raise ValueError("Некорректная координата элемента.")

    return result


def build_lines(nodes, links, stored_edges):
    """
    Подготовить линии для размещений.

    Для нескольких размещений одного объекта показываются все
    сочетания размещений исходного и целевого объектов.

    Связи репозитория и сохранённые линии V14 остаются раздельными.
    """
    normalized_nodes = {}
    placements = {}

    for node in nodes:
        node_id = key(node["id"])
        object_id = (key(node['object_id']) if node.get('object_id') is not None else None)

        normalized_nodes[node_id] = {
            "id": node_id,
            "object_id": object_id,
            "x": _number(node["x"]),
            "y": _number(node["y"]),
            "width": _number(node.get("width", 180)),
            "height": _number(node.get("height", 70)),
        }

        placements.setdefault(object_id, []).append(node_id)

    lines = []

    for link in links:
        source_id = key(link["source_id"])
        target_id = key(link["target_id"])
        code = str(link["link_type"])
        label = LINK_NAMES.get(code, code)

        for source_node in placements.get(source_id, []):
            for target_node in placements.get(target_id, []):
                if source_node == target_node:
                    continue

                lines.append({
                    "source": source_node,
                    "target": target_node,
                    "label": label,
                    "kind": "repository",
                })

    for edge in stored_edges:
        source_node = key(edge["source_node_id"])
        target_node = key(edge["target_node_id"])

        # Неполную линию не показываем, но и не меняем её в состоянии.
        if (
            source_node not in normalized_nodes
            or target_node not in normalized_nodes
            or source_node == target_node
        ):
            continue

        lines.append({
            "source": source_node,
            "target": target_node,
            "label": str(edge.get("label") or "Линия V14"),
            "kind": "stored",
            "edge_id": key(edge["id"]),
        })

    return normalized_nodes, lines


def render_svg(nodes, links, stored_edges, width, height):
    """
    Сформировать безопасную SVG-разметку.

    Пользовательские подписи экранируются. Координаты проверяются.
    Линии затем позиционируются JavaScript-кодом редактора.
    """
    normalized_nodes, lines = build_lines(
        nodes,
        links,
        stored_edges,
    )

    marker_id = "rs-arrow-" + uuid.uuid4().hex

    parts = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{int(width)}" height="{int(height)}" '
            f'viewBox="0 0 {int(width)} {int(height)}" '
            'style="display:block;overflow:visible;pointer-events:none">'
        ),
        "<defs>",
        (
            f'<marker id="{marker_id}" '
            'viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M 0 0 L 10 5 L 0 10 z" '
            'fill="context-stroke"></path></marker>'
        ),
        "</defs>",
    ]

    # Смещаем параллельные линии, чтобы несколько отношений
    # между одной парой размещений не совпадали полностью.
    totals = {}

    for line in lines:
        pair = tuple(sorted((line["source"], line["target"])))
        totals[pair] = totals.get(pair, 0) + 1

    positions = {}

    for line in lines:
        pair = tuple(sorted((line["source"], line["target"])))
        index = positions.get(pair, 0)
        positions[pair] = index + 1

        offset = (index - (totals[pair] - 1) / 2) * 16

        source = html.escape(line["source"], quote=True)
        target = html.escape(line["target"], quote=True)
        label = html.escape(line["label"], quote=True)

        if line["kind"] == "repository":
            color = "#60a5fa"
            dash = ""
        else:
            color = "#fbbf24"
            dash = ' stroke-dasharray="6 4"'


        # RS_DIAGRAM_FLOW_TYPES_V29_RENDER
        flow_styles = {
            "__RS_FLOW_V29__:MESSAGE": (
                "#c084fc", ' stroke-dasharray="8 5"',
                "Поток сообщений",
            ),
            "__RS_FLOW_V29__:CONTROL": (
                "#e2e8f0", "", "Поток управления",
            ),
            "__RS_FLOW_V29__:DEFAULT": (
                "#fbbf24", "", "В остальных случаях",
            ),
            "__RS_FLOW_V29__:CONDITIONAL": (
                "#4ade80", "", "Условие",
            ),
        }
        if (
            line["kind"] == "stored"
            and line["label"] in flow_styles
        ):
            color, dash, display_label = flow_styles[line["label"]]
            label = ""  # RS_BPMN_REPOSITORY_FLOWS_V43
        # RS_DIAGRAM_EDIT_FLOW_V33
        flow_codes_v33 = {
            "__RS_FLOW_V29__:MESSAGE",
            "__RS_FLOW_V29__:CONTROL",
            "__RS_FLOW_V29__:DEFAULT",
            "__RS_FLOW_V29__:CONDITIONAL",
        }
        flow_edge_attr_v33 = ""
        if (
            line["kind"] == "stored"
            and line["label"] in flow_codes_v33
        ):
            safe_edge_v33 = html.escape(line["edge_id"], quote=True)
            flow_edge_attr_v33 = (
                f' data-rs-flow-edge="{safe_edge_v33}"'
            )

        parts.append(
            f'<g class="rs-smart-line"{flow_edge_attr_v33} '
            f'data-source="{source}" '
            f'data-target="{target}" '
            f'data-offset="{offset}">'
            f'<line stroke="{color}" stroke-width="2"'
            f'{dash} marker-end="url(#{marker_id})"></line>'
            '<text text-anchor="middle" '
            'font-size="12" fill="#ffffff" '
            'paint-order="stroke" stroke="#17202c" '
            'stroke-width="4" stroke-linejoin="round">'
            f'{label}</text>'
            '</g>'
        )

    parts.append("</svg>")

    return "".join(parts), len(lines)


def self_test():
    a = uuid.uuid4().hex
    b = uuid.uuid4().hex
    node_a = uuid.uuid4().hex
    node_b = uuid.uuid4().hex

    nodes = [
        {
            "id": node_a,
            "object_id": a,
            "x": 10,
            "y": 20,
            "width": 180,
            "height": 70,
        },
        {
            "id": node_b,
            "object_id": b,
            "x": 300,
            "y": 40,
            "width": 180,
            "height": 70,
        },
    ]

    links = [{
        "source_id": a,
        "target_id": b,
        "link_type": "USES",
    }]

    stored = [{
        "source_node_id": node_b,
        "target_node_id": node_a,
        "label": "<проверка>",
    }]

    markup, count = render_svg(nodes, links, stored, 900, 500)

    assert count == 2
    assert "Использует" in markup
    assert "&lt;проверка&gt;" in markup
    assert "<проверка>" not in markup
    assert node_a in markup and node_b in markup

    _, one_node_lines = build_lines(nodes[:1], links, stored)
    assert one_node_lines == []

    duplicate = dict(nodes[0])
    duplicate["id"] = uuid.uuid4().hex

    _, duplicate_lines = build_lines(
        nodes + [duplicate],
        links,
        [],
    )
    assert len(duplicate_lines) == 2

    print("SMART_LINK_HELPER_TESTS_OK")


# RS_BPMN_FLOW_MARKERS_V38
# Сохраняем исходную функцию, чтобы не менять подготовку линий.
_rs_render_svg_before_v38 = render_svg


def render_svg(nodes, links, stored_edges, width, height):
    """
    Добавить маркеры только к известным потокам V29.

    Технические связи репозитория и произвольные старые линии
    сохраняют прежний вид и не изменяются.
    """
    import uuid as _uuid
    import xml.etree.ElementTree as _ET

    markup, count = _rs_render_svg_before_v38(
        nodes, links, stored_edges, width, height
    )

    flow_kinds = {
        key(edge["id"]): str(edge.get("label") or "")
        for edge in stored_edges
        if str(edge.get("label") or "") in {
            "__RS_FLOW_V29__:MESSAGE",
            "__RS_FLOW_V29__:CONTROL",
            "__RS_FLOW_V29__:DEFAULT",
            "__RS_FLOW_V29__:CONDITIONAL",
        }
    }

    if not flow_kinds:
        return markup, count

    svg_ns = "http://www.w3.org/2000/svg"
    q = lambda name: "{" + svg_ns + "}" + name
    _ET.register_namespace("", svg_ns)

    root = _ET.fromstring(markup)
    defs = root.find(q("defs"))

    if defs is None:
        raise ValueError("В SVG отсутствует раздел маркеров.")

    unique = "rs-bpmn-v38-" + _uuid.uuid4().hex

    def make_marker(name, view_box, ref_x, ref_y, path, fill, stroke):
        marker_id = unique + "-" + name
        marker = _ET.SubElement(
            defs,
            q("marker"),
            {
                "id": marker_id,
                "viewBox": view_box,
                "refX": str(ref_x),
                "refY": str(ref_y),
                "markerWidth": "10",
                "markerHeight": "10",
                "markerUnits": "userSpaceOnUse",
                "orient": "auto",
                "overflow": "visible",
            },
        )
        _ET.SubElement(
            marker,
            q("path"),
            {
                "d": path,
                "fill": fill,
                "stroke": stroke,
                "stroke-width": "1.4",
            },
        )
        return "url(#" + marker_id + ")"

    filled_end = make_marker(
        "filled-end", "0 0 10 10", 9, 5,
        "M 0 0 L 10 5 L 0 10 Z",
        "context-stroke", "context-stroke",
    )

    open_end = make_marker(
        "open-end", "0 0 10 10", 9, 5,
        "M 0 0 L 9 5 L 0 10",
        "none", "context-stroke",
    )

    diamond_start = make_marker(
        "diamond-start", "0 0 14 10", 0, 5,
        "M 0 5 L 7 0 L 14 5 L 7 10 Z",
        "#17202c", "context-stroke",
    )

    slash_start = make_marker(
        "slash-start", "0 0 10 12", 2, 6,
        "M 0 11 L 6 1",
        "none", "context-stroke",
    )

    circle_start = make_marker(
        "circle-start", "0 0 10 10", 0, 5,
        "M 0 5 A 5 5 0 1 0 10 5 A 5 5 0 1 0 0 5 Z",
        "#17202c", "context-stroke",
    )

    for group in root.iter(q("g")):
        edge_id = group.get("data-rs-flow-edge")

        if not edge_id or edge_id not in flow_kinds:
            continue

        line = group.find(q("line"))
        if line is None:
            continue

        kind = flow_kinds[edge_id]

        if kind == "__RS_FLOW_V29__:MESSAGE":
            line.set("marker-start", circle_start)
            line.set("marker-end", open_end)
            line.set("stroke-dasharray", "8 5")
        else:
            line.set("marker-end", filled_end)

            if kind == "__RS_FLOW_V29__:CONDITIONAL":
                line.set("marker-start", diamond_start)
            elif kind == "__RS_FLOW_V29__:DEFAULT":
                line.set("marker-start", slash_start)

    return _ET.tostring(root, encoding="unicode"), count
