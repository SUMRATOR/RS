# RS_INSTALLER_BUILD_V60
"""Сборка установщика RS — RUBIK STUDIO.

Порядок:

1. ``python build_rubik_exe.py`` — собирает папку ``dist/RUBIK_STUDIO``
   (PyInstaller).
2. ``python build_installer.py`` — упаковывает её в установщик
   ``installer/RS_RUBIK_STUDIO_<версия>_setup.exe`` через Inno Setup.

Скрипт намеренно не пытается «починить» отсутствие Inno Setup сам:
он проверяет типичные пути установки, пишет понятную инструкцию и
возвращает код ошибки. Молча создавать пустой установщик нельзя — так
пользователь получит файл, который «устанавливается» и не работает.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
SPEC = PROJECT / "installer" / "RS_RUBIK_STUDIO.iss"
DIST = PROJECT / "dist" / "RUBIK_STUDIO"
EXE = DIST / "RUBIK_STUDIO.exe"

# Типичные места установки Inno Setup 6.
ISCC_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
)


def find_iscc() -> Path | None:
    """Найти компилятор Inno Setup."""
    env_path = os.environ.get("ISCC_PATH")
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return candidate

    for candidate in ISCC_CANDIDATES:
        if candidate.is_file():
            return candidate

    found = shutil.which("iscc") or shutil.which("ISCC")
    if found:
        return Path(found)

    return None


def check_dist() -> None:
    """Проверить, что программа уже собрана."""
    if not EXE.is_file():
        raise SystemExit(
            "Папка сборки не найдена: "
            f"{EXE}\n"
            "Сначала выполните: python build_rubik_exe.py"
        )


def print_install_hint() -> None:
    print()
    print("=" * 60)
    print("INNO SETUP НЕ НАЙДЕН")
    print("=" * 60)
    print("Установщик собирается компилятором Inno Setup 6.")
    print("Скачайте его: https://jrsoftware.org/isdl.php")
    print("После установки повторите: python build_installer.py")
    print()
    print("Если Inno Setup установлен в другое место, укажите путь:")
    print(r'  set ISCC_PATH=C:\путь\к\ISCC.exe')
    print()
    print("Уже собранную программу можно запускать и без установщика:")
    print(f"  {EXE}")


def build(iscc: Path) -> Path:
    """Собрать установщик и вернуть путь к файлу."""
    if not SPEC.is_file():
        raise SystemExit(f"Не найден файл установщика: {SPEC}")

    print("Сборка установщика…")
    result = subprocess.run(
        [str(iscc), str(SPEC)],
        cwd=PROJECT,
        check=False,
    )

    if result.returncode != 0:
        raise SystemExit(
            f"Inno Setup завершился с кодом {result.returncode}. "
            "Подробности — в выводе выше и в installer/setup.log."
        )

    produced = sorted(
        (PROJECT / "installer").glob("RS_RUBIK_STUDIO_*_setup.exe")
    )
    if not produced:
        raise SystemExit(
            "Компилятор завершился без ошибок, но установщик не найден. "
            "Проверьте папку installer."
        )

    return produced[-1]


def main() -> int:
    print("=" * 60)
    print("RS — RUBIK STUDIO")
    print("СОЗДАНИЕ УСТАНОВЩИКА")
    print("=" * 60)
    print(f"Проект: {PROJECT}")

    check_dist()

    iscc = find_iscc()
    if iscc is None:
        print_install_hint()
        return 2

    print(f"Компилятор: {iscc}")
    setup = build(iscc)

    print()
    print("=" * 60)
    print("УСТАНОВЩИК ГОТОВ")
    print("=" * 60)
    print(setup)
    print(f"Размер: {setup.stat().st_size / (1024 * 1024):.1f} МБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
