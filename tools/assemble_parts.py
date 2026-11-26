#!/usr/bin/env python3
"""Собирает части архива (.001, .002, ...) обратно и проверяет целостность.

Нужен, если архив резался через `make_archive.py --split N` для загрузки
на GitHub (там лимит 25 МБ на файл).

    python assemble_parts.py rubik-studio-src-20261126-1813.zip
    # прочитает .001, .002, ... и создаст rubik-studio-src-20261126-1813.zip

    python assemble_parts.py --extract rubik-studio-src-20261126-1813.zip
    # то же самое + распакует в папку с тем же именем
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path


def human(num: float) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if abs(num) < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} ТБ"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    extract = "--extract" in sys.argv[1:]
    if len(args) != 1:
        print("Использование: python assemble_parts.py <архив.zip> [--extract]")
        return 2

    target = Path(args[0]).expanduser().resolve()
    parts = sorted(target.parent.glob(target.name + ".[0-9][0-9][0-9]"))

    if not parts:
        if target.exists():
            print(f"ℹ Частей не найдено — уже собранный файл: {target}")
        else:
            print(f"✗ Не найдено ни частей, ни файла: {target}")
            return 1
    else:
        # Проверяем, что нумерация непрерывная — иначе архив будет битым.
        expected = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        indexes = [int(p.suffix[1:]) for p in parts]
        if indexes != list(range(1, len(parts) + 1)):
            print(f"✗ Пропущены части! Есть: {indexes}")
            print("  Скачай/загрузи все части заново.")
            return 1
        print(f"📎 Найдено частей: {len(parts)} ({human(sum(p.stat().st_size for p in parts))})")
        with target.open("wb") as out:
            for p in parts:
                print(f"   + {p.name}  {human(p.stat().st_size)}")
                out.write(p.read_bytes())
        print(f"\n📦 Собран: {target} ({human(target.stat().st_size)})")

    print("🔍 Проверяю целостность...")
    try:
        with zipfile.ZipFile(target) as zf:
            bad = zf.testzip()
            count = len(zf.namelist())
            if bad is not None:
                print(f"✗ Повреждён файл внутри архива: {bad}")
                return 1
            print(f"✔ Архив цел, внутри {count} файлов")
            if extract:
                out_dir = target.with_suffix("")
                zf.extractall(out_dir)
                print(f"📂 Распакован в: {out_dir}")
    except zipfile.BadZipFile:
        print("✗ Это не zip-архив или он повреждён (части неполные?).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
