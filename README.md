# RS — RUBIK STUDIO

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Status](https://img.shields.io/badge/status-Этап%201-orange)

> **Model. Mine. Automate.**

Открытая платформа для моделирования, анализа (Process Mining) и автоматизации
(BPMS) бизнес-процессов. Работает как десктопное приложение (одно окно,
без браузера) или как сервер для командной работы.

## 🚀 Быстрый старт

```bash
git clone https://github.com/SUMRATOR/RS.git
cd RS
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m rubik_studio           # десктопное окно (pywebview)
python -m rubik_studio --server  # сервер: http://127.0.0.1:8080
```

Параметры запуска: `--server`, `--host 0.0.0.0`, `--port 8080`.

При первом запуске создаётся папка `data/` с базой SQLite (`rubik_studio.db`),
конфигом (`config.json`) и логами (`app.log`). Она в `.gitignore` — там
локальные пути и `secret_key`.

## 🧱 Структура проекта

```
rubik_studio/
├── main.py                    # точка входа, маршруты, ui.run
├── config.py                  # AppConfig: desktop/server, БД, secret_key
├── auth/                      # вход, роли, пользователи
├── core/                      # ядро без зависимости от UI
│   ├── database.py            # async SQLAlchemy, бэкапы, seed-данные
│   ├── models.py              # объекты, базы моделирования, диаграммы, аудит
│   ├── repository.py          # CRUD объектов и связей по базам
│   ├── modeling_databases.py  # логические базы, методологии, модели
│   ├── diagram_storage_v15.py # хранение диаграмм
│   ├── diagram_symbols_v39.py # библиотека символов
│   ├── bpmn_foundation_v35.py # основа BPMN
│   ├── object_templates_v8.py # шаблоны объектов
│   └── validators.py          # валидация имён, BPMN XML, CSV, учётных данных
└── ui/
    ├── layout.py              # хедер, сайдбар, уведомления, диалоги
    └── pages/                 # страницы NiceGUI
        ├── dashboard.py       # главная: сводка по базам и объектам
        ├── login.py           # вход
        ├── repository.py      # объекты выбранной базы
        ├── modeling_databases.py
        ├── logs_viewer.py     # аудит-логи
        ├── settings.py        # режимы и пользователи
        ├── object_templates_v8.py, object_links_v10.py, repository_types_v6.py
        ├── diagram_create_v20.py, diagram_editor_v16.py,
        │   diagram_smart_links_v23.py, canvas_draft_v11.py
        └── experimental_bpmn_v40.py, experimental_diagrams_v22.py
```

## 🗺 Дорожная карта

| Этап | Что делаем | Статус |
|---|---|---|
| 1 | Репозиторий объектов, базы моделирования, аудит-логи, desktop/server | 🟡 в работе |
| 2 | BPMN-моделирование | 🟡 прототипы (`*_v16…v40`) |
| 3 | Process Mining (импорт CSV, анализ журналов событий) | ⬜ запланировано |
| 4 | BPMS (исполнение процессов, задачи) | ⬜ запланировано |
| 5 | Генерация регламентов (DOCX) | ⬜ запланировано |

## ✅ Состояние

Проверено запуском `python -m rubik_studio --server` на Python 3.11
(NiceGUI 4.1.0, SQLAlchemy 2.1.9): все маршруты отвечают `200` —
`/`, `/login`, `/dashboard`, `/repository`, `/logs`, `/settings`,
`/modeling-databases`.

Известные ограничения:

- страницы `experimental_*.py` и `canvas_draft_v11.py` не подключены к
  маршрутам — это эксперименты, не часть интерфейса;
- тестов (`tests/`) в проекте пока нет, хотя CI их ожидает.

## 🛠 Сборка exe

```bash
pip install pyinstaller
python build_rubik_exe.py     # или build_rubik_studio.cmd на Windows
```

Конфигурация PyInstaller — `RUBIK_STUDIO.spec`.

## 📤 Передача проекта в репозиторий

Если архив проекта большой, см. **[tools/КАК-ПЕРЕДАТЬ-ПРОЕКТ.md](tools/КАК-ПЕРЕДАТЬ-ПРОЕКТ.md)**.
Кратко: `git push` напрямую или чистый архив, собранный
`python tools/make_archive.py <папка проекта> --split 24`.

## 📄 Лицензия

MIT — см. [LICENSE.txt](LICENSE.txt).
