from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
ASSETS = PROJECT / "rubik_studio" / "assets"


def run(command):
    print()
    print("Выполняется:")
    print(" ".join(map(str, command)))

    result = subprocess.run(
        command,
        cwd=PROJECT,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Команда завершилась с кодом {result.returncode}"
        )


def main():
    print("=" * 60)
    print("RS — RUBIK STUDIO")
    print("СОЗДАНИЕ АВТОНОМНОЙ WINDOWS-СБОРКИ")
    print("=" * 60)

    if not PROJECT.is_dir():
        raise RuntimeError("Папка проекта не найдена")

    # Установка PyInstaller.
    run([
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pyinstaller",
    ])

    # Создание временной точки входа.
    launcher = PROJECT / "_rubik_exe_launcher.py"

    launcher.write_text(
        """
from rubik_studio.main import main

if __name__ == "__main__":
    main()
""".strip() + "\n",
        encoding="utf-8",
    )

    # Сборка.
    run([
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        "RUBIK_STUDIO",
        "--collect-all",
        "nicegui",
        "--collect-all",
        "webview",
        "--collect-all",
        "sqlalchemy",
        "--collect-all",
        "aiosqlite",
        "--collect-all",
        "passlib",
        "--collect-all",
        "bcrypt",
        # RS_EXE_ASSETS_FIX_V1
        "--add-data",
        str(ASSETS) + ";rubik_studio/assets",
        str(launcher),
    ])

    print()
    print("=" * 60)
    print("СБОРКА ЗАВЕРШЕНА")
    print("=" * 60)

    print()
    print("Папка программы:")
    print(PROJECT / "dist" / "RUBIK_STUDIO")

    print()
    print("Запускаемый файл:")
    print(
        PROJECT
        / "dist"
        / "RUBIK_STUDIO"
        / "RUBIK_STUDIO.exe"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print("ОШИБКА:", type(exc).__name__, exc)
