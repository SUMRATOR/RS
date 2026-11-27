#!/usr/bin/env python3
# RS_CI_REPORT_V57
"""Печатает упавшие тесты как аннотации GitHub Actions.

Зачем: строки лога прогона в интерфейсе GitHub не всегда открываются
(внешнее хранилище логов бывает недоступно), а аннотации показываются
прямо на странице проверки. Поэтому pytest пишет отчёт JUnit XML, а этот
скрипт превращает его в строки ``::error::`` с именем теста и сообщением.

    python tools/ci_report_F.py report.xml

Код возврата 0, если падений нет, и 1, если есть — так шаг CI остаётся
красным, но с понятной причиной.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

LIMIT = 12  # сколько падений показывать подробно


def _clean(text: str) -> str:
    """Схлопнуть переводы строк: аннотация GitHub однострочная."""
    return " ".join((text or "").split())[:900]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Укажите путь к отчёту JUnit: ci_report_F.py report.xml")
        return 2

    report = Path(args[0])
    if not report.exists():
        print(f"::error title=CI::Отчёт pytest не создан: {report}")
        return 1

    try:
        root = ET.parse(report).getroot()
    except ET.ParseError as exc:
        print(f"::error title=CI::Не удалось прочитать отчёт: {exc}")
        return 1

    cases = root.iter("testcase")
    failed: list[tuple[str, str, str]] = []
    total = 0

    for case in cases:
        total += 1
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if problem is None:
            continue
        name = case.get("name", "?")
        classname = case.get("classname", "")
        message = problem.get("message") or (problem.text or "")
        failed.append((f"{classname}::{name}" if classname else name, _clean(message), classname))

    if not failed:
        print(f"Все тесты прошли ({total}).")
        return 0

    print(f"::error title=CI::Упало тестов: {len(failed)} из {total}")

    for name, message, classname in failed[:LIMIT]:
        title = _clean(name)[:120]
        print(f"::error title={title}:: {message}")

    if len(failed) > LIMIT:
        print(f"… ещё {len(failed) - LIMIT} падений, см. отчёт {report.name}")

    # Короткая сводка в обычном тексте — на случай, если аннотации не видны.
    print("\nУпавшие тесты:")
    for name, message, _ in failed:
        print(f"  ✗ {name}")
        print(f"    {message[:300]}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
