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
pip install -r requirements.txt
python -m rubik_studio
```

> ⚠️ **Текущее состояние:** в репозитории лежит неполная версия Этапа 1 —
> отсутствует точка входа `rubik_studio/main.py`, а `ui/pages/settings.py`
> обрывается на середине. Приложение в таком виде не запускается.
> См. раздел «Статус миграции» ниже.

## 📦 Структура проекта

```
rubik_studio/
├── __init__.py            # версия и имя приложения
├── __main__.py            # запуск через python -m rubik_studio
├── config.py              # AppConfig: режимы desktop/server, БД, secret_key
├── auth/
│   ├── middleware.py      # текущий пользователь, вход/выход, require_auth
│   └── users.py           # аутентификация, создание и удаление пользователей
├── core/                  # ядро: не зависит от UI
│   ├── audit_logger.py    # аудит-логи в БД + ротируемые системные логи
│   ├── database.py        # async SQLAlchemy, бэкапы SQLite, seed-данные
│   ├── models.py          # Object/ObjectType/User/BPMN/Process Mining/BPMS
│   ├── repository.py      # CRUD объектов и связей репозитория
│   └── validators.py      # валидация имён, BPMN XML, CSV, учётных данных
└── ui/                    # тонкий слой NiceGUI
    ├── layout.py          # хедер, сайдбар, уведомления, диалоги
    └── pages/
        ├── dashboard.py   # главная со статистикой
        ├── login.py       # вход
        ├── logs_viewer.py # таблица аудит-логов
        ├── onboarding.py  # приветственный диалог первого запуска
        ├── repository.py  # репозиторий объектов
        └── settings.py    # ⚠️ файл обрезан — требует восстановления
```

## 🗺 Дорожная карта

| Этап | Что делаем | Статус |
|---|---|---|
| 1 | Репозиторий объектов, аудит-логи, режимы desktop/server | 🟡 в работе |
| 2 | BPMN-моделирование | ⬜ запланировано |
| 3 | Process Mining (импорт CSV, анализ журналов событий) | ⬜ запланировано |
| 4 | BPMS (исполнение процессов, задачи) | ⬜ запланировано |
| 5 | Генерация регламентов (DOCX) | ⬜ запланировано |

## 🛠 Статус миграции

Код перенесён из репозитория [`SUMRATOR/rubit-studio-test`](https://github.com/SUMRATOR/rubit-studio-test)
в этот репозиторий (корень проекта, без вложенной папки).

Выявленные при переносе дефекты исходного репозитория:

1. **Нет `rubik_studio/main.py`** — `pyproject.toml` и `__main__.py` импортируют
   `rubik_studio.main:main`, но файла нет. Приложение не запускается.
2. **`ui/pages/settings.py` обрезан** на строке 37
   (`if config.mode == "server" and user.get`) — синтаксическая ошибка.
3. **`pyproject.tolm`** — опечатка в имени файла (должно быть `.toml`),
   поэтому `pip install .` не видит метаданные.
4. **Нет страниц** `modeler.py`, `mining.py`, `bpms.py`, хотя пункты меню в
   `ui/layout.py` на них ссылаются, и нет папки `tests/`.

## 📄 Лицензия

MIT — см. [LICENSE.txt](LICENSE.txt).

## 📤 Как передать проект в репозиторий

Если архив проекта большой (сотни мегабайт) — см.
**[tools/КАК-ПЕРЕДАТЬ-ПРОЕКТ.md](tools/КАК-ПЕРЕДАТЬ-ПРОЕКТ.md)**.
Кратко: `git push` напрямую или чистый архив, собранный
`python tools/make_archive.py <папка проекта> --split 24`.
