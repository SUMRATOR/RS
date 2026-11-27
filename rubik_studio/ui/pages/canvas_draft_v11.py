# RS_CANVAS_REFRESH_FIX_V18
# RS_CANVAS_DRAFT_MODULE_V11
# RS_CANVAS_MOUSE_V12
# RS_CANVAS_SAVE_V13
#
# Сохраняемый экспериментальный черновик.
# Это не модель BPMN/VAD и не таблица model_element_bindings.

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import math
import os
import tempfile
import uuid
from pathlib import Path

try:  # RS_FILELOCK_PORTABLE_V55
    import msvcrt  # Windows: блокировка через msvcrt.locking
except ModuleNotFoundError:  # pragma: no cover - не-Windows (CI, Linux, macOS)
    msvcrt = None
    import fcntl

from nicegui import ui

from rubik_studio.core.repository import RepositoryService

repository_service = RepositoryService()


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "rs_canvas_drafts"
BACKUP_DIR = DATA_DIR / "backups"

CANVAS_WIDTH = 900
CANVAS_HEIGHT = 500
NODE_WIDTH = 180
NODE_HEIGHT = 70
MAX_NODES = 500
MAX_FILE_BYTES = 5 * 1024 * 1024


class DraftError(Exception):
    pass


class DraftConflict(DraftError):
    pass


def _database_key(database_id) -> str:
    value = str(database_id).strip()

    if not value:
        raise DraftError("Не указан идентификатор базы.")

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _paths(database_id):
    key = _database_key(database_id)
    return DATA_DIR / (key + ".json"), DATA_DIR / (key + ".lock")


class _FileLock:
    """Межпроцессная блокировка для экземпляров приложения на Windows."""

    def __init__(self, path: Path):
        self.path = path
        self.file = None

    def __enter__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, "a+b")

        # Для блокировки нужен хотя бы один байт.
        self.file.seek(0, os.SEEK_END)
        if self.file.tell() == 0:
            self.file.write(b"0")
            self.file.flush()

        self.file.seek(0)

        try:
            if msvcrt is not None:
                msvcrt.locking(self.file.fileno(), msvcrt.LK_LOCK, 1)
            else:
                # На POSIX достаточно блокировки файла — приложение
                # основной целевой платформы (Windows) не затрагивается.
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX)
        except Exception:
            self.file.close()
            self.file = None
            raise

        return self

    def __exit__(self, exc_type, exc, tb):
        if self.file is not None:
            try:
                self.file.seek(0)
                if msvcrt is not None:
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            finally:
                self.file.close()
                self.file = None


def _number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DraftError("В файле черновика обнаружена неверная координата.")

    value = float(value)

    if not math.isfinite(value):
        raise DraftError("В файле черновика обнаружена неверная координата.")

    return max(low, min(high, value))


def _validate_document(data, database_id):
    if not isinstance(data, dict):
        raise DraftError("Неверный формат файла черновика.")

    if data.get("format") != "rs_canvas_draft_v13":
        raise DraftError("Неизвестный формат файла черновика.")

    if data.get("database_id") != str(database_id):
        raise DraftError("Файл черновика относится к другой базе.")

    revision = data.get("revision")

    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise DraftError("Неверная версия черновика.")

    raw_nodes = data.get("nodes")

    if not isinstance(raw_nodes, list) or len(raw_nodes) > MAX_NODES:
        raise DraftError("Неверный список элементов черновика.")

    result = []
    used_ids = set()

    for item in raw_nodes:
        if not isinstance(item, dict):
            raise DraftError("Неверный элемент черновика.")

        node_id = item.get("id")
        object_id = item.get("object_id")

        if not isinstance(node_id, str) or not node_id or len(node_id) > 128:
            raise DraftError("Неверный идентификатор элемента.")

        if node_id in used_ids:
            raise DraftError("В черновике повторяется идентификатор элемента.")

        if not isinstance(object_id, str) or not object_id or len(object_id) > 128:
            raise DraftError("Неверный идентификатор объекта.")

        used_ids.add(node_id)

        result.append({
            "id": node_id,
            "object_id": object_id,
            "x": _number(item.get("x"), 0, CANVAS_WIDTH - NODE_WIDTH),
            "y": _number(item.get("y"), 0, CANVAS_HEIGHT - NODE_HEIGHT),
        })

    return revision, result


def _read_unlocked(path, database_id):
    if not path.exists():
        return 0, []

    if not path.is_file():
        raise DraftError("Путь черновика не является файлом.")

    if path.stat().st_size > MAX_FILE_BYTES:
        raise DraftError("Файл черновика слишком большой.")

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError) as exc:
        raise DraftError(
            "Не удалось прочитать черновик. Файл не перезаписан: " + str(exc)
        ) from exc

    return _validate_document(data, database_id)


def load_draft(database_id):
    path, lock_path = _paths(database_id)

    with _FileLock(lock_path):
        return _read_unlocked(path, database_id)


def save_draft(database_id, expected_revision, nodes):
    path, lock_path = _paths(database_id)

    with _FileLock(lock_path):
        current_revision, _ = _read_unlocked(path, database_id)

        if current_revision != expected_revision:
            raise DraftConflict(
                "Черновик уже изменён в другом окне. "
                "Сохранение отменено. Закройте это окно и откройте черновик заново."
            )

        document = {
            "format": "rs_canvas_draft_v13",
            "database_id": str(database_id),
            "revision": current_revision + 1,
            "saved_at": datetime.datetime.now(
                datetime.UTC
            ).isoformat(),
            "nodes": copy.deepcopy(nodes),
        }

        # Перед записью проверяем и собственные данные.
        _validate_document(document, database_id)

        encoded = json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")

        if len(encoded) > MAX_FILE_BYTES:
            raise DraftError("Черновик слишком большой для сохранения.")

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Снимок предыдущей версии перед заменой.
        if path.exists():
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)

            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup = BACKUP_DIR / (
                path.stem + "_" + stamp + "_" + uuid.uuid4().hex[:8] + ".json"
            )

            with path.open("rb") as source, backup.open("xb") as destination:
                while True:
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    destination.write(block)

                destination.flush()
                os.fsync(destination.fileno())

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=path.stem + "_",
                suffix=".tmp",
                dir=DATA_DIR,
                delete=False,
            ) as file:
                temp_path = Path(file.name)
                file.write(encoded)
                file.flush()
                os.fsync(file.fileno())

            os.replace(temp_path, path)
            temp_path = None

        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

        return document["revision"]


def _error_text(exc):
    text = str(exc).strip()
    return text if text else type(exc).__name__


async def open_canvas_draft(database_id, database_name):
    """Открыть один сохраняемый черновик выбранной логической базы."""

    try:
        objects = await repository_service.list_objects(database_id)
        revision, loaded_nodes = load_draft(database_id)
    except Exception as exc:
        ui.notify(
            "Не удалось открыть черновик: " + _error_text(exc),
            type="negative",
            timeout=10000,
        )
        return

    state = {
        "revision": revision,
        "nodes": loaded_nodes,
        "selected": None,
        "object_id": None,
        "dirty": False,
        "objects": {str(obj.id): str(obj.name) for obj in objects},
    }

    def options():
        return {
            str(obj.id): f"{obj.name}  [{str(obj.id)[:8]}]"
            for obj in objects
        }

    def set_dirty():
        state["dirty"] = True
        status.set_text("Есть несохранённые изменения")

    def choose_node(node_id):
        state["selected"] = node_id
        draw_canvas.refresh()

    def moved(node_id, event):
        detail = event.args

        if isinstance(detail, dict) and "detail" in detail:
            detail = detail["detail"]

        if not isinstance(detail, dict):
            return

        try:
            x = _number(detail.get("x"), 0, CANVAS_WIDTH - NODE_WIDTH)
            y = _number(detail.get("y"), 0, CANVAS_HEIGHT - NODE_HEIGHT)
        except DraftError:
            return

        for node in state["nodes"]:
            if node["id"] == node_id:
                if node["x"] != x or node["y"] != y:
                    node["x"] = x
                    node["y"] = y
                    set_dirty()
                break

    @ui.refreshable
    def draw_canvas():
        with ui.element("div").style(
            f"position:relative; width:{CANVAS_WIDTH}px; "
            f"height:{CANVAS_HEIGHT}px; min-width:{CANVAS_WIDTH}px; "
            "overflow:hidden; border:1px solid #526174; "
            "border-radius:10px; background-color:#17202c; "
            "background-image:"
            "linear-gradient(#ffffff0a 1px, transparent 1px),"
            "linear-gradient(90deg, #ffffff0a 1px, transparent 1px);"
            "background-size:25px 25px;"
        ):
            for node in state["nodes"]:
                node_id = node["id"]
                object_id = node["object_id"]
                name = state["objects"].get(object_id)
                missing = name is None

                if missing:
                    name = "Объект отсутствует: " + object_id[:8]

                selected = state["selected"] == node_id

                border = (
                    "#f87171" if missing
                    else "#38bdf8" if selected
                    else "#718096"
                )

                with ui.element("div").style(
                    "position:absolute; "
                    f"left:{node['x']}px; top:{node['y']}px; "
                    f"width:{NODE_WIDTH}px; height:{NODE_HEIGHT}px; "
                    "box-sizing:border-box; "
                    f"border:2px solid {border}; "
                    "border-radius:9px; background:#273649; "
                    "color:white; padding:8px; cursor:grab; "
                    "touch-action:none; user-select:none; "
                    "overflow:hidden; z-index:1;"
                ) as element:
                    ui.label(name).style(
                        "font-size:14px; line-height:18px; "
                        "overflow:hidden; overflow-wrap:anywhere;"
                    )

                    if missing:
                        ui.label("Удалите элемент с полотна").style(
                            "font-size:10px; color:#fca5a5;"
                        )

                element.on(
                    "click",
                    lambda e, n=node_id: choose_node(n),
                )

                element.on(
                    "rs-canvas-moved",
                    lambda e, n=node_id: moved(n, e),
                    args=["detail"],
                )

                # В JavaScript передаётся только числовой ID компонента.
                # Имя и другие данные пользователя в код JS не вставляются.
                ui.run_javascript(
                    """
                    (() => {
                        const el = document.getElementById('cCOMPONENT_ID');
                        if (!el || el.dataset.rsDragReady === '1') return;
                        el.dataset.rsDragReady = '1';

                        let startX = 0;
                        let startY = 0;
                        let left = 0;
                        let top = 0;
                        let active = false;

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
                                0, Math.min(720, left + e.clientX - startX)
                            );
                            const y = Math.max(
                                0, Math.min(430, top + e.clientY - startY)
                            );
                            el.style.left = x + 'px';
                            el.style.top = y + 'px';
                        });

                        function finish(e) {
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
                    })();
                    """.replace("COMPONENT_ID", str(element.id))
                )

    def add_node():
        object_id = state["object_id"]

        if not object_id or object_id not in state["objects"]:
            ui.notify("Сначала выберите объект из репозитория.", type="warning")
            return

        if len(state["nodes"]) >= MAX_NODES:
            ui.notify("Достигнут предел элементов черновика.", type="warning")
            return

        index = len(state["nodes"])
        x = 20 + (index % 4) * 210
        y = 20 + ((index // 4) % 5) * 90

        node = {
            "id": str(uuid.uuid4()),
            "object_id": object_id,
            "x": x,
            "y": y,
        }

        state["nodes"].append(node)
        state["selected"] = node["id"]
        set_dirty()
        draw_canvas.refresh()

    def remove_node():
        selected = state["selected"]

        if not selected:
            ui.notify("Сначала выберите элемент на полотне.", type="warning")
            return

        before = len(state["nodes"])
        state["nodes"] = [
            node for node in state["nodes"] if node["id"] != selected
        ]
        state["selected"] = None

        if len(state["nodes"]) != before:
            set_dirty()
            draw_canvas.refresh()

    async def save():
        try:
            # Проверяем принадлежность каждого объекта выбранной базе
            # непосредственно перед сохранением.
            current_objects = await repository_service.list_objects(database_id)
            current_names = {
                str(obj.id): str(obj.name) for obj in current_objects
            }

            missing = [
                node for node in state["nodes"]
                if node["object_id"] not in current_names
            ]

            state["objects"] = current_names

            if missing:
                draw_canvas.refresh()
                ui.notify(
                    "Сохранение отменено: некоторые объекты отсутствуют "
                    "в этой базе. Удалите отмеченные элементы с полотна.",
                    type="negative",
                    timeout=10000,
                )
                return

            state["revision"] = save_draft(
                database_id,
                state["revision"],
                state["nodes"],
            )
            state["dirty"] = False
            status.set_text(
                f"Сохранено. Версия: {state['revision']}"
            )
            draw_canvas.refresh()
            ui.notify("Черновик сохранён.", type="positive")

        except DraftConflict as exc:
            ui.notify(str(exc), type="negative", timeout=12000)
        except Exception as exc:
            ui.notify(
                "Не удалось сохранить черновик: " + _error_text(exc),
                type="negative",
                timeout=12000,
            )

    def request_close():
        if not state["dirty"]:
            dialog.close()
            return

        with ui.dialog() as confirm, ui.card():
            ui.label("Есть несохранённые изменения. Закрыть черновик?")
            with ui.row():
                ui.button(
                    "Продолжить работу",
                    on_click=confirm.close,
                ).props("flat")

                def discard_and_close():
                    confirm.close()
                    dialog.close()

                ui.button(
                    "Закрыть без сохранения",
                    on_click=discard_and_close,
                    color="negative",
                )

        confirm.open()

    with ui.dialog() as dialog, ui.card().style(
        "width:1100px; max-width:96vw; max-height:94vh; overflow:auto;"
    ):
        dialog.props("persistent")

        ui.label(f"Черновик полотна — {database_name}").style(
            "font-size:20px; font-weight:600;"
        )

        ui.label(
            "Один черновик на базу. Перетаскивайте элементы мышью. "
            "После изменений нажмите «Сохранить»."
        ).style("color:#94a3b8;")

        with ui.row().classes("items-center w-full"):
            # Элемент нужен интерфейсу; ссылка на него не используется.
            ui.select(
                options=options(),
                label="Объект репозитория",
                on_change=lambda e: state.update({"object_id": e.value}),
            ).style("min-width:300px;")

            ui.button("Добавить", on_click=add_node, icon="add")
            ui.button(
                "Удалить элемент",
                on_click=remove_node,
                icon="delete_outline",
            ).props("outline")

            ui.button("Сохранить", on_click=save, icon="save", color="primary")
            ui.button("Закрыть", on_click=request_close).props("flat")

        status = ui.label(
            f"Загружено. Версия: {state['revision']}"
        ).style("color:#94a3b8;")

        with ui.element("div").style("max-width:100%; overflow:auto;"):
            draw_canvas()

        ui.label(
            "Удаление элемента с полотна не удаляет объект репозитория. "
            "Связи и линии пока не поддерживаются."
        ).style("font-size:12px; color:#94a3b8;")

    dialog.open()
