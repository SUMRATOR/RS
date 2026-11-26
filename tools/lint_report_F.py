#!/usr/bin/env python3
# RS_LINT_REPORT_V57
"""Отчёт о стилистическом долге унаследованного кода.

В `pyproject.toml` осознанно включены только правила, которые ловят
настоящие ошибки (синтаксис, неопределённые имена, мёртвые импорты,
порядок импортов). Стилистические правила отключены, потому что их
правка в рабочем коде меняет поведение интерфейса без нужды.

Этот скрипт показывает, что именно осталось за рамками — чтобы долг был
виден и сокращался, а не был спрятан. Падение он не вызывает: это отчёт.

    python tools/lint_report_F.py            # сводка по правилам
    python tools/lint_report_F.py --files    # ещё и по файлам
"""

from __future__ import annotations

import argparse
import collections
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Стилистические наборы, отключённые в pyproject.toml. Смотрим их отдельно.
DEBT_SELECT = "BLE,SIM,EXE,PLW"


def run_ruff(*args: str) -> tuple[int, str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format=concise", *args],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )
    except FileNotFoundError:
        return 127, "ruff не установлен"
    return result.returncode, result.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Отчёт о стилистическом долге")
    parser.add_argument("--files", action="store_true", help="показать разбивку по файлам")
    args = parser.parse_args(argv)

    code, output = run_ruff(f"--select={DEBT_SELECT}", ".")
    if code == 127:
        print(output)
        return 1

    lines = [line for line in output.splitlines() if ": " in line and not line.startswith("Found")]
    counts = collections.Counter()
    by_file = collections.Counter()

    for line in lines:
        parts = line.split(": ", 1)
        location, rule = parts[0], parts[1].split(" ", 1)[0]
        counts[rule] += 1
        by_file[location.split(":")[0]] += 1

    print("Стилистический долг унаследованного кода (не блокирует CI)")
    print("-" * 56)
    if not counts:
        print("нарушений нет")
        return 0

    for rule, number in counts.most_common():
        print(f"{rule:<10} {number:>4}")

    print(f"{'всего':<10} {sum(counts.values()):>4}")

    if args.files:
        print("\nПо файлам:")
        for name, number in by_file.most_common():
            print(f"{number:>4}  {name}")

    print(
        "\nЭто осознанно отложенные правила: BLE001 (широкий except в UI-коде), "
        "SIM117 (вложенные with в NiceGUI), EXE001 (shebang у скриптов), "
        "PLW1510 (subprocess без check)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
