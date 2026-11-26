from __future__ import annotations

# RS_PERSISTENT_CONFIG_V1

import json
import logging
import os
import secrets
import sys

from dataclasses import asdict, dataclass, field
from pathlib import Path


logger = logging.getLogger("rubik_studio")


def _get_base_dir() -> Path:
    """
    Исходники:
        rubik-studio/

    Автономный EXE:
        %LOCALAPPDATA%/RUBIK_STUDIO/
    """

    if getattr(sys, "frozen", False):
        local = os.environ.get("LOCALAPPDATA")

        if not local:
            raise RuntimeError(
                "Не найдена переменная LOCALAPPDATA."
            )

        return Path(local) / "RUBIK_STUDIO"

    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()

DATA_DIR = BASE_DIR / "data"

CONFIG_PATH = DATA_DIR / "config.json"

CONFIG_BACKUP_PATH = DATA_DIR / "config.json.bak"


def _default_db_path() -> str:
    return str(DATA_DIR / "rubik_studio.db")


def _default_log_path() -> str:
    return str(DATA_DIR / "app.log")


def _is_old_frozen_path(value: str) -> bool:
    """
    Определяет старый путь к данным внутри
    каталога PyInstaller _internal.
    """

    if not value:
        return False

    normalized = value.replace(
        "\\", "/"
    ).lower()

    return (
        "/_internal/data/" in normalized
        or "/dist/rubik_studio/data/" in normalized
    )


@dataclass
class AppConfig:
    mode: str = "desktop"
    host: str = "127.0.0.1"
    port: int = 8080

    db_type: str = "sqlite"
    db_path: str = field(
        default_factory=_default_db_path
    )
    db_url: str = ""

    auth_enabled: bool = False

    secret_key: str = field(
        default_factory=lambda: secrets.token_hex(32)
    )

    log_level: str = "INFO"
    audit_log_enabled: bool = True

    log_file: str = field(
        default_factory=_default_log_path
    )

    first_run_done: bool = False

    # RS_THEMES_V56: оформление интерфейса.
    # theme — light | dark | hacker | custom;
    # theme_accent и theme_background — цвета «своей тёмной» темы.
    theme: str = "dark"
    theme_accent: str = "#7C5CFF"
    theme_background: str = "#14121D"

    def get_db_url(self) -> str:
        if (
            self.db_type == "postgresql"
            and self.db_url
        ):
            return self.db_url

        path = Path(self.db_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        return (
            "sqlite+aiosqlite:///"
            + path.as_posix()
        )

    def switch_to_server(
        self,
        host: str = "0.0.0.0",
        port: int = 8080
    ) -> None:

        self.mode = "server"
        self.host = host
        self.port = port
        self.auth_enabled = True
        self.save()

    def switch_to_desktop(self) -> None:

        self.mode = "desktop"
        self.host = "127.0.0.1"
        self.auth_enabled = False
        self.save()

    def save(self) -> None:

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        try:
            if CONFIG_PATH.exists():
                CONFIG_PATH.replace(
                    CONFIG_BACKUP_PATH
                )

        except OSError as exc:
            logger.warning(
                "Не удалось создать резервную копию "
                "конфигурации: %s",
                exc
            )

        try:
            with CONFIG_PATH.open(
                "w",
                encoding="utf-8"
            ) as fh:

                json.dump(
                    asdict(self),
                    fh,
                    ensure_ascii=False,
                    indent=2
                )

        except OSError as exc:
            logger.error(
                "Не удалось сохранить конфигурацию: %s",
                exc
            )

    @classmethod
    def load(cls) -> "AppConfig":

        if not CONFIG_PATH.exists():
            cfg = cls()
            cfg.save()
            return cfg

        try:
            with CONFIG_PATH.open(
                "r",
                encoding="utf-8"
            ) as fh:
                raw = json.load(fh)

            known = set(
                cls.__dataclass_fields__
            )

            cfg = cls(
                **{
                    k: v
                    for k, v in raw.items()
                    if k in known
                }
            )

            # Исправляем исключительно старые пути
            # автономной версии.
            if getattr(sys, "frozen", False):

                changed = False

                if _is_old_frozen_path(
                    cfg.db_path
                ):
                    cfg.db_path = (
                        _default_db_path()
                    )
                    changed = True

                if _is_old_frozen_path(
                    cfg.log_file
                ):
                    cfg.log_file = (
                        _default_log_path()
                    )
                    changed = True

                if changed:
                    cfg.save()

            return cfg

        except (
            json.JSONDecodeError,
            OSError
        ) as exc:

            logger.error(
                "Ошибка конфигурации: %s",
                exc
            )

            if CONFIG_BACKUP_PATH.exists():

                try:
                    with CONFIG_BACKUP_PATH.open(
                        "r",
                        encoding="utf-8"
                    ) as fh:
                        raw = json.load(fh)

                    known = set(
                        cls.__dataclass_fields__
                    )

                    cfg = cls(
                        **{
                            k: v
                            for k, v in raw.items()
                            if k in known
                        }
                    )

                    if getattr(
                        sys, "frozen", False
                    ):
                        if _is_old_frozen_path(
                            cfg.db_path
                        ):
                            cfg.db_path = (
                                _default_db_path()
                            )

                        if _is_old_frozen_path(
                            cfg.log_file
                        ):
                            cfg.log_file = (
                                _default_log_path()
                            )

                    return cfg

                except (
                    json.JSONDecodeError,
                    OSError
                ):
                    pass

            return cls()



# RS_PORTABLE_DATABASE_FIX_V2

# RS_PORTABLE_PATHS_FIX_V3

def _repair_portable_paths(cfg):
    """
    В исходной версии исправляет устаревшие стандартные пути,
    оставшиеся после переноса проекта.

    Произвольные пользовательские пути не изменяются.
    Конфигурация автоматически на диск не записывается.
    """

    if getattr(sys, "frozen", False):
        return cfg

    def is_stale_default_path(value, filename):
        if not isinstance(value, str) or not value:
            return False

        path = Path(value)

        if not path.is_absolute():
            return False

        # Существующий путь не перенаправляем.
        if path.exists():
            return False

        normalized = value.replace("\\", "/").lower()

        return normalized.endswith(
            "/rubik-studio/data/" + filename.lower()
        )

    if (
        cfg.db_type == "sqlite"
        and is_stale_default_path(
            cfg.db_path,
            "rubik_studio.db",
        )
    ):
        candidate = Path(_default_db_path())

        # Не создаём новую пустую SQLite вместо потерянной.
        if not candidate.is_file():
            raise RuntimeError(
                "Старый путь SQLite недоступен, а база данных "
                f"не найдена в текущем проекте: {candidate}. "
                "Восстановите или укажите нужную базу данных."
            )

        logger.warning(
            "Устаревший путь SQLite заменён на базу "
            "текущего проекта: %s",
            candidate,
        )

        cfg.db_path = str(candidate)

    if is_stale_default_path(cfg.log_file, "app.log"):
        candidate = Path(_default_log_path())

        logger.warning(
            "Устаревший путь журнала заменён на путь "
            "текущего проекта: %s",
            candidate,
        )

        cfg.log_file = str(candidate)

    return cfg


config = _repair_portable_paths(AppConfig.load())
