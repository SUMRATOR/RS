# RS_LOGO_FIX_V57
"""Подготовка логотипа RS для ленты тем оформления.

Исходник ``rubik_studio/assets/rubik_logo.png`` — 1254×1254 на сплошном
белом фоне без альфа-канала. На тёмной, hacker и «своей тёмной» темах
такой файл выглядит белым прямоугольником, а тёмно-синяя надпись на нём
не читается. Поэтому скрипт собирает три производных файла:

* ``rubik_logo_light.png`` — прозрачный фон, исходные цвета (светлая тема);
* ``rubik_logo_dark.png``  — прозрачный фон, детали осветлены в фирменный
  синий (тёмная, hacker, «своя тёмная»);
* ``rubik_logo_mark.png``  — только знак куба без надписи, для шапки, где
  логотип показывается размером 30 px и подпись всё равно не читается.

Прозрачным считается только светлый почти-серый фон: у настоящих деталей
логотипа есть насыщенность (синий, голубой), поэтому проверяется ещё и
разброс между каналами.

Скрипт разработки по SPEC §0.2 (``*_F.py``). Приложение пользуется уже
готовыми PNG и не требует Pillow во время работы.

    python tools/logo_prepare_F.py            # пересобрать все версии
    python tools/logo_prepare_F.py --check    # только проверить наличие
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "rubik_studio" / "assets"
SOURCE = ASSETS / "rubik_logo.png"

LIGHT_VERSION = ASSETS / "rubik_logo_light.png"
DARK_VERSION = ASSETS / "rubik_logo_dark.png"
MARK_VERSION = ASSETS / "rubik_logo_mark.png"

# Светлый почти-серый — это подложка. Порог и допуск по насыщенности.
WHITE_LIMIT = 238
NEUTRAL_SPREAD = 14

# Тёмно-синие детали (надпись, грань куба) на тёмном фоне пропадают.
INK_LIMIT = 90
BRAND_BLUE = (122, 178, 255)

# Границы частей исходника (найдены по строкам с непрозрачными пикселями).
MARK_BOTTOM = 790  # выше этой строки — только куб


def _is_background(r: int, g: int, b: int) -> bool:
    return min(r, g, b) > WHITE_LIMIT and max(r, g, b) - min(r, g, b) < NEUTRAL_SPREAD


def _edge_alpha(r: int, g: int, b: int) -> int:
    """Частичная прозрачность у границы с подложкой — край без «пилы»."""
    if min(r, g, b) > 200 and max(r, g, b) - min(r, g, b) < 40:
        return max(0, min(255, round(255 * (255 - min(r, g, b)) / 55)))
    return 255


def _to_brand_blue(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Осветлить тёмно-синюю деталь к фирменному синему, сохранив светлоту."""
    darkness = (INK_LIMIT - max(r, g, b)) / INK_LIMIT
    k = 0.35 + 0.55 * darkness
    return (
        round(r + (BRAND_BLUE[0] - r) * k),
        round(g + (BRAND_BLUE[1] - g) * k),
        round(b + (BRAND_BLUE[2] - b) * k),
    )


def _build(lighten_ink: bool, crop_mark: bool):
    from PIL import Image

    source = Image.open(SOURCE).convert("RGB")
    if crop_mark:
        source = source.crop((0, 0, source.width, MARK_BOTTOM))

    pixels = source.load()
    width, height = source.size
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    out_pixels = out.load()

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            if _is_background(r, g, b):
                continue
            alpha = _edge_alpha(r, g, b)
            if lighten_ink and max(r, g, b) < INK_LIMIT:
                r, g, b = _to_brand_blue(r, g, b)
            out_pixels[x, y] = (r, g, b, alpha)

    box = out.getbbox()
    if box:
        out = out.crop(box)

    # Квадрат с прозрачными полями: в шапке и на главной логотип
    # вписывается в квадратную область без искажений.
    side = max(out.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(out, ((side - out.width) // 2, (side - out.height) // 2))
    square.thumbnail((512, 512), Image.LANCZOS)
    return square


def build_all() -> list[Path]:
    targets = [
        (LIGHT_VERSION, False, False),
        (DARK_VERSION, True, False),
        (MARK_VERSION, True, True),
    ]
    made = []
    for path, lighten, crop in targets:
        image = _build(lighten_ink=lighten, crop_mark=crop)
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, "PNG", optimize=True)
        made.append(path)
    return made


def check() -> bool:
    ok = True
    for path in (SOURCE, LIGHT_VERSION, DARK_VERSION, MARK_VERSION):
        exists = path.exists()
        print(f"{'есть ' if exists else 'НЕТ  '} {path.relative_to(ROOT)}")
        ok = ok and exists
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Подготовка логотипа RS для тем оформления")
    parser.add_argument("--check", action="store_true", help="только проверить наличие файлов")
    args = parser.parse_args(argv)

    if args.check:
        return 0 if check() else 1

    if not SOURCE.exists():
        print(f"Нет исходного логотипа: {SOURCE}", file=sys.stderr)
        return 1

    try:
        made = build_all()
    except ImportError:
        print(
            "Нужен Pillow: pip install pillow. Готовые версии уже лежат в assets, "
            "запуск нужен только после замены логотипа.",
            file=sys.stderr,
        )
        return 1

    for path in made:
        print(f"готово: {path.relative_to(ROOT)} ({path.stat().st_size // 1024} КБ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
