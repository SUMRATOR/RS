#!/usr/bin/env python3
"""Собирает чистый архив проекта Rubik Studio для передачи.

Скрипт нужен, чтобы 500 МБ «распухшего» архива превратились в 2–15 МБ
исходников: он исключает виртуальные окружения, кэши, базы данных, сборки
и прочий мусор, а затем показывает, что именно занимало место.

Использование (из любой папки, Python 3.9+):

    # 1. Посмотреть, что занимает место, и собрать архив
    python make_archive.py "C:\\Users\\Имя\\Documents\\rubik-studio"

    # 2. Разбить архив на части по 24 МБ (если GitHub не принимает файл)
    python make_archive.py "C:\\путь\\к\\проекту" --split 24

Результат: rubik-studio-src-<дата>.zip рядом с исходной папкой (или в --out).
Части: .zip.001, .zip.002, ... — загружать на GitHub нужно ВСЕ части.
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Папки, которые никогда не нужны в архиве исходников.
EXCLUDE_DIRS = {
    ".git", ".hg", ".svn",
    ".venv", "venv", "env", "ENV", "virtualenv",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    "node_modules", "bower_components",
    "build", "dist", "out", "target",
    ".idea", ".vscode",
    "htmlcov", "site-packages",
    ".eggs",
}

# Маски файлов-мусора.
EXCLUDE_SUFFIXES = {
    ".pyc", ".pyo", ".pyd",
    ".log",
    ".db", ".db-journal", ".sqlite", ".sqlite3",
    ".bak",
    ".exe", ".dll", ".so", ".dylib",
    ".zip", ".7z", ".rar", ".tar", ".gz",
    ".mp4", ".mov", ".avi", ".iso",
}
# Резервные копии БД вида rubik_studio.db.bak1
EXCLUDE_PREFIXES = ("rubik_studio.db.bak",)

# Данные приложения, которые нужны только на твоей машине.
EXCLUDE_DATA_DIRS = {"data", "uploads", "logs"}

MAX_FILE_BYTES = 20 * 1024 * 1024  # отдельные файлы крупнее 20 МБ не шлём


def human(num: float) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if abs(num) < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} ТБ"


def is_excluded_file(name: str) -> bool:
    if name.startswith(EXCLUDE_PREFIXES):
        return True
    return Path(name).suffix.lower() in EXCLUDE_SUFFIXES


def scan(root: Path) -> tuple[list[Path], dict[str, int], list[tuple[int, str]]]:
    """Возвращает (файлы_для_архива, вес_по_категориям, крупнейшие_файлы)."""
    keep: list[Path] = []
    excluded_size: dict[str, int] = {}
    big: list[tuple[int, str]] = []

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        rel_dir = current.relative_to(root)

        # Отсекаем мусорные папки целиком (и не спускаемся в них).
        pruned = []
        for d in list(dirnames):
            if d in EXCLUDE_DIRS or (d in EXCLUDE_DATA_DIRS and rel_dir == Path(".")):
                size = 0
                for p in (current / d).rglob("*"):
                    if p.is_file():
                        size += p.stat().st_size
                excluded_size[f"{rel_dir / d}" if rel_dir != Path(".") else d] = size
                pruned.append(d)
        for d in pruned:
            dirnames.remove(d)

        for name in filenames:
            path = current / name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            rel = path.relative_to(root)
            if is_excluded_file(name):
                excluded_size[str(rel)] = size
                continue
            if size > MAX_FILE_BYTES:
                excluded_size[str(rel)] = size
                big.append((size, str(rel)))
                continue
            keep.append(rel)

    return keep, excluded_size, sorted(big, reverse=True)


def build_zip(root: Path, files: list[Path], out: Path) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in files:
            zf.write(root / rel, arcname=str(rel))


def split_file(src: Path, part_mb: int) -> list[Path]:
    part = part_mb * 1024 * 1024
    parts: list[Path] = []
    with src.open("rb") as fh:
        index = 1
        while True:
            chunk = fh.read(part)
            if not chunk:
                break
            target = src.with_name(f"{src.name}.{index:03d}")
            target.write_bytes(chunk)
            parts.append(target)
            index += 1
    return parts


def main() -> int:
    parser = argparse.ArgumentParser(description="Собирает чистый архив проекта.")
    parser.add_argument("source", help="папка проекта, например C:\\путь\\к\\rubik-studio")
    parser.add_argument("--out", default=None, help="куда положить архив (по умолчанию рядом)")
    parser.add_argument(
        "--split", type=int, default=0, metavar="МБ",
        help="разбить архив на части указанного размера (например 24)",
    )
    args = parser.parse_args()

    root = Path(args.source).expanduser().resolve()
    if not root.is_dir():
        print(f"✗ Папка не найдена: {root}", file=sys.stderr)
        return 1

    print(f"\n📂 Проект: {root}\n")
    files, excluded, big = scan(root)

    total_keep = sum((root / f).stat().st_size for f in files)
    total_excluded = sum(excluded.values())

    print(f"✅ В архив пойдёт: {len(files)} файлов, {human(total_keep)}")
    print(f"🗑  Будет исключено: {human(total_excluded)}\n")

    if excluded:
        print("Что исключено (крупнейшее):")
        for name, size in sorted(excluded.items(), key=lambda kv: kv[1], reverse=True)[:15]:
            print(f"   {human(size):>10}  {name}")
        print()

    if big:
        print("⚠ Отдельные файлы больше 20 МБ (тоже исключены):")
        for size, name in big[:10]:
            print(f"   {human(size):>10}  {name}")
        print("   Если такой файл нужен для работы — скажи, добавим его отдельно.\n")

    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out_dir = Path(args.out).expanduser().resolve() if args.out else root.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{root.name}-src-{stamp}.zip"

    print("⏳ Сжимаю...")
    build_zip(root, files, out)
    size = out.stat().st_size
    print(f"\n📦 Готово: {out}")
    print(f"   Размер архива: {human(size)}")

    if args.split and size > args.split * 1024 * 1024:
        parts = split_file(out, args.split)
        out.unlink()
        print(f"\n✂ Разбито на {len(parts)} частей по {args.split} МБ:")
        for p in parts:
            print(f"   {p.name}  ({human(p.stat().st_size)})")
        print("\nЗагрузи на GitHub ВСЕ части .001, .002, ... — я соберу их обратно.")
    elif size > 25 * 1024 * 1024:
        print("\n⚠ Файл больше 25 МБ — веб-загрузка GitHub его не примет.")
        print("   Запусти ещё раз с флагом --split 24 и загрузи все части.")
    else:
        print("\n✔ Файл меньше 25 МБ — можно загружать на GitHub через Add file → Upload files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
