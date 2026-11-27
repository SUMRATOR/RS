# RS_THEMES_V56
"""Темы оформления Rubik Studio.

Четыре темы, переключаемые без перезапуска:

* ``light``    — светлая, тёплая (песочная), без сине-белого неона;
* ``dark``     — тёмная, нейтральная;
* ``hacker``   — монохромный зелёный на почти чёрном, для любителей;
* ``custom``   — пользовательская тёмная: базовые цвета берутся из темы
                 ``dark``, акцент и фон задаёт пользователь.

Модуль не импортирует NiceGUI: он отдаёт только словари с CSS-переменными
и готовый CSS. Благодаря этому темы можно проверить автотестом
(контраст, полнота набора токенов) без браузера.

Контраст: цвета подобраны так, чтобы основной текст на фоне давал
не менее 4.5:1 (WCAG AA), крупные заголовки — не менее 3:1.
В автотесте ``test_contrast.py`` это проверяется расчётом.
"""

from __future__ import annotations

from dataclasses import dataclass, field

THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_HACKER = "hacker"
THEME_CUSTOM = "custom"

THEME_ORDER = (THEME_LIGHT, THEME_DARK, THEME_HACKER, THEME_CUSTOM)

# Метаданные для интерфейса настроек.
THEME_INFO: dict[str, dict[str, str]] = {
    THEME_LIGHT: {
        "name": "Светлая",
        "description": "Тёплая песочная палитра без синевы: спокойный фон, тёмный текст.",
        "swatch": "#F6F2EA",
    },
    THEME_DARK: {
        "name": "Тёмная",
        "description": "Нейтральная тёмная тема для долгой работы днём и вечером.",
        "swatch": "#161B22",
    },
    THEME_HACKER: {
        "name": "Hacker",
        "description": "Зелёный монохром на почти чёрном фоне: терминальный стиль.",
        "swatch": "#00A86B",
    },
    THEME_CUSTOM: {
        "name": "Своя тёмная",
        "description": "Тёмная основа с вашим цветом акцента и фоном.",
        "swatch": "#7C5CFF",
    },
}


# Фон поля диаграммы. Одинаков во всех темах осознанно: цвета символов BPMN
# (bpmn_shapes_v55.COLOR) рассчитаны именно на этот фон и по требованию
# пользователя от темы не зависят. Тема меняет интерфейс вокруг поля,
# но не перекрашивает нотацию.
NOTATION_CANVAS_BG = "#17202C"


@dataclass
class ThemePalette:
    """Набор цветовых токенов одной темы.

    Имена токенов одинаковы для всех тем, поэтому интерфейс красится
    через CSS-переменные и не знает, какая тема активна.
    """

    name: str
    bg: str               # фон приложения
    surface: str          # карточки, панели
    surface_alt: str      # второй уровень (строки таблиц, поповеры)
    border: str
    text: str             # основной текст
    text_muted: str       # подписи, пояснения
    primary: str          # кнопки, ссылки, акцент
    primary_text: str     # текст на primary
    success: str
    warning: str
    danger: str
    canvas_bg: str        # фон полотна диаграммы
    canvas_grid: str      # линии сетки полотна
    canvas_node: str      # фон узла диаграммы
    canvas_edge: str      # линии связей
    font_family: str = "'Segoe UI', system-ui, -apple-system, sans-serif"
    extra: dict[str, str] = field(default_factory=dict)

    def as_css_vars(self) -> str:
        """CSS-переменные вида ``--rs-bg: #F6F2EA;`` для вставки в <style>."""
        tokens = {
            "bg": self.bg,
            "surface": self.surface,
            "surface-alt": self.surface_alt,
            "border": self.border,
            "text": self.text,
            "text-muted": self.text_muted,
            "primary": self.primary,
            "primary-text": self.primary_text,
            "success": self.success,
            "warning": self.warning,
            "danger": self.danger,
            "canvas-bg": self.canvas_bg,
            "canvas-grid": self.canvas_grid,
            "canvas-node": self.canvas_node,
            "canvas-edge": self.canvas_edge,
            "font-family": self.font_family,
        }
        tokens.update(self.extra)
        return "\n".join(f"  --rs-{key}: {value};" for key, value in tokens.items())


# ── Тёплая светлая: песок, охра, глубокий графит ────────────────────────────
LIGHT = ThemePalette(
    name=THEME_LIGHT,
    bg="#F6F2EA",
    surface="#FFFFFF",
    surface_alt="#EFE8DC",
    border="#D9CFBE",
    text="#2A2622",
    text_muted="#6B6058",
    primary="#A2541B",       # охра: читаемый акцент вместо синего
    primary_text="#FFFFFF",
    success="#2F6B3C",
    warning="#8A5A00",
    danger="#A32B2B",
    canvas_bg=NOTATION_CANVAS_BG,
    canvas_grid="#252D39",   # NOTATION_CANVAS_BG, осветлённый на 6%
    canvas_node=NOTATION_CANVAS_BG,
    canvas_edge="#7A6E60",
)

# ── Нейтральная тёмная ─────────────────────────────────────────────────────
DARK = ThemePalette(
    name=THEME_DARK,
    bg="#161B22",
    surface="#1E2B45",
    surface_alt="#243351",
    border="#33415C",
    text="#E8EDF5",
    text_muted="#A9B8CF",
    primary="#7FB2FF",
    primary_text="#0F172A",
    success="#4ED6A0",
    warning="#FFC857",
    danger="#FF8A8A",
    canvas_bg=NOTATION_CANVAS_BG,
    canvas_grid="#252D39",   # NOTATION_CANVAS_BG, осветлённый на 6%
    canvas_node=NOTATION_CANVAS_BG,
    canvas_edge="#8FA3BF",
)

# ── Hacker: зелёный монохром ───────────────────────────────────────────────
HACKER = ThemePalette(
    name=THEME_HACKER,
    bg="#050A07",
    surface="#0A1510",
    surface_alt="#0E1D16",
    border="#1D3A2B",
    text="#B9F6CE",
    text_muted="#6FBF8B",
    primary="#39FF88",
    primary_text="#03110A",
    success="#39FF88",
    warning="#D7FF5A",
    danger="#FF6B6B",
    canvas_bg=NOTATION_CANVAS_BG,
    canvas_grid="#252D39",   # NOTATION_CANVAS_BG, осветлённый на 6%
    canvas_node=NOTATION_CANVAS_BG,
    canvas_edge="#39FF88",
    font_family="'JetBrains Mono', 'Consolas', 'Courier New', monospace",
)

THEMES: dict[str, ThemePalette] = {
    THEME_LIGHT: LIGHT,
    THEME_DARK: DARK,
    THEME_HACKER: HACKER,
    # «Своя тёмная» базируется на DARK, цвета подменяются пользователем.
    THEME_CUSTOM: DARK,
}


def _clamp_byte(value: int) -> int:
    return max(0, min(255, value))


class ColorError(ValueError, TypeError):
    """Некорректный цвет. Наследует и ValueError, и TypeError.

    Так вызывающий код может ловить ошибку как ValueError (мусор в
    config.json) и как TypeError (передан не тот тип), не дублируя ветки.
    """


def parse_hex(color: str) -> tuple[int, int, int]:
    """``#RRGGBB`` → (r, g, b). Некорректный цвет вызывает ColorError."""
    if not isinstance(color, str):
        raise ColorError("Цвет должен быть строкой в формате #RRGGBB")
    text = color.strip()
    if not text.startswith("#"):
        text = "#" + text
    if len(text) != 7:
        raise ColorError("Цвет должен быть в формате #RRGGBB")
    try:
        return tuple(int(text[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]
    except ValueError as exc:
        raise ColorError("Цвет должен быть в формате #RRGGBB") from exc


def to_hex(r: int, g: int, b: int) -> str:
    return f"#{_clamp_byte(r):02X}{_clamp_byte(g):02X}{_clamp_byte(b):02X}"


def relative_luminance(color: str) -> float:
    """Относительная яркость по WCAG 2.x."""
    def channel(value: int) -> float:
        srgb = value / 255
        return srgb / 12.92 if srgb <= 0.04045 else ((srgb + 0.055) / 1.055) ** 2.4

    r, g, b = parse_hex(color)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(first: str, second: str) -> float:
    """Коэффициент контраста двух цветов: от 1:1 до 21:1."""
    a = relative_luminance(first)
    b = relative_luminance(second)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def readable_text_color(background: str) -> str:
    """Тёмный или светлый текст — что даёт больший контраст на фоне."""
    dark = "#0B0F14"
    light = "#FFFFFF"
    return dark if contrast_ratio(background, dark) >= contrast_ratio(background, light) else light


def mix(first: str, second: str, amount: float) -> str:
    """Смешать два цвета: amount=0 → first, amount=1 → second."""
    amount = max(0.0, min(1.0, amount))
    r1, g1, b1 = parse_hex(first)
    r2, g2, b2 = parse_hex(second)
    return to_hex(
        round(r1 + (r2 - r1) * amount),
        round(g1 + (g2 - g1) * amount),
        round(b1 + (b2 - b1) * amount),
    )


# Граница «тёмности» фона: средняя яркость канала. Выше — фон уже не
# тёмный, и пользовательская тема перестаёт быть тёмной.
DARKNESS_LIMIT = 60.0


def is_dark_enough(background: str) -> bool:
    """Фон достаточно тёмный для «своей тёмной» темы."""
    r, g, b = parse_hex(background)
    return (r + g + b) / 3 <= DARKNESS_LIMIT


def normalize_background(background: str) -> str:
    """Привести фон к тёмному оттенку, сохранив выбранный тон.

    Пользователь задаёт цвет-подсветку; фон остаётся тёмным в том же
    тоне. Слишком светлый фон затемняется до предела DARKNESS_LIMIT.
    """
    r, g, b = parse_hex(background)
    average = (r + g + b) / 3
    if average <= DARKNESS_LIMIT:
        return to_hex(r, g, b)

    factor = DARKNESS_LIMIT / average
    return to_hex(round(r * factor), round(g * factor), round(b * factor))


def custom_palette(accent: str = "#7C5CFF", background: str = "#14121D") -> ThemePalette:
    """Пользовательская тёмная тема.

    Пользователь задаёт акцент («подсветку») и фон. Фон всегда остаётся
    тёмным: слишком светлый приводится к тёмному оттенку того же тона.
    Остальные токены выводятся автоматически, чтобы тема оставалась
    читаемой и не превращалась в «кашу».
    """
    accent = to_hex(*parse_hex(accent))
    background = normalize_background(background)

    surface = mix(background, "#FFFFFF", 0.06)
    surface_alt = mix(background, "#FFFFFF", 0.10)
    border = mix(background, "#FFFFFF", 0.20)

    return ThemePalette(
        name=THEME_CUSTOM,
        bg=background,
        surface=surface,
        surface_alt=surface_alt,
        border=border,
        text=readable_text_color(background),
        text_muted=mix(readable_text_color(background), background, 0.35),
        primary=accent,
        primary_text=readable_text_color(accent),
        success="#4ED6A0",
        warning="#FFC857",
        danger="#FF8A8A",
        canvas_bg=NOTATION_CANVAS_BG,
        canvas_grid=mix(NOTATION_CANVAS_BG, "#FFFFFF", 0.06),
        canvas_node=NOTATION_CANVAS_BG,
        canvas_edge=mix(accent, "#FFFFFF", 0.25),
    )


def palette_for(
    theme: str,
    accent: str | None = None,
    background: str | None = None,
) -> ThemePalette:
    """Палитра по имени темы. Для ``custom`` — с учётом цветов пользователя."""
    if theme == THEME_CUSTOM:
        return custom_palette(accent or "#7C5CFF", background or "#14121D")
    if theme not in THEMES:
        raise ValueError(f"Неизвестная тема: {theme}")
    return THEMES[theme]


def build_css(palette: ThemePalette) -> str:
    """Готовый CSS: переменные, фон, типографика, компоненты NiceGUI/Quasar."""
    dark = palette.name != THEME_LIGHT
    return f""":root {{
{palette.as_css_vars()}
}}

html, body {{
  background: var(--rs-bg) !important;
  color: var(--rs-text) !important;
  font-family: var(--rs-font-family);
}}

.rs-app-shell {{
  background: var(--rs-bg);
  color: var(--rs-text);
}}

.nicegui-content, .q-page {{
  background: var(--rs-bg) !important;
  color: var(--rs-text) !important;
}}

/* Шапка и боковое меню */
header.q-header, .q-header {{
  background: var(--rs-surface) !important;
  color: var(--rs-text) !important;
  border-bottom: 1px solid var(--rs-border);
}}

.q-drawer, .q-drawer .q-drawer__content {{
  background: var(--rs-surface) !important;
  color: var(--rs-text) !important;
  border-right: 1px solid var(--rs-border);
}}

/* Карточки, диалоги, списки */
.q-card, .q-dialog .q-card, .q-menu, .q-popup-proxy {{
  background: var(--rs-surface) !important;
  color: var(--rs-text) !important;
  border: 1px solid var(--rs-border);
}}

.q-list, .q-item {{
  color: var(--rs-text) !important;
}}

.q-item:hover {{
  background: var(--rs-surface-alt) !important;
}}

/* Поля ввода */
.q-field__control {{
  background: var(--rs-surface-alt) !important;
  border-radius: 8px;
}}

.q-field__native, .q-field__input,
.q-field__label, .q-field__marginal {{
  color: var(--rs-text) !important;
}}

.q-field--outlined .q-field__control:before {{
  border-color: var(--rs-border) !important;
}}

/* Кнопки */
.q-btn {{
  text-transform: none;
  letter-spacing: 0;
  font-weight: 600;
}}

.q-btn--flat, .q-btn--outline {{
  color: var(--rs-text) !important;
}}

/* Таблицы */
.q-table, .q-table__card {{
  background: var(--rs-surface) !important;
  color: var(--rs-text) !important;
}}

.q-table th {{
  color: var(--rs-text-muted) !important;
  font-weight: 600;
}}

.q-table tbody tr:hover {{
  background: var(--rs-surface-alt) !important;
}}

/* Тонкие подписи */
.rs-muted {{
  color: var(--rs-text-muted) !important;
}}

/* Шапка и боковое меню: классы из layout.py */
header.rs-header {{
  background: var(--rs-surface) !important;
  color: var(--rs-text) !important;
  border-bottom: 1px solid var(--rs-border);
  box-shadow: none;
}}

.rs-sidebar {{
  background: var(--rs-surface) !important;
  color: var(--rs-text) !important;
  border-right: 1px solid var(--rs-border);
}}

.rs-sidebar .q-btn {{
  color: var(--rs-text) !important;
  justify-content: flex-start;
}}

.rs-sidebar .q-btn:hover {{
  background: var(--rs-surface-alt) !important;
  color: var(--rs-primary) !important;
}}

/* Приглушённые подписи внутри контента */
.rs-app-shell .text-gray-500,
.rs-app-shell .text-gray-400,
.rs-app-shell .text-slate-400 {{
  color: var(--rs-text-muted) !important;
}}

/* Ссылки и акцентные подписи */
a, .rs-accent {{
  color: var(--rs-primary);
}}

/* Полотно диаграммы */
.rs-canvas {{
  background-color: var(--rs-canvas-bg) !important;
  border-color: var(--rs-border) !important;
}}

/* Скроллбары в тёмных темах */
{'' if not dark else '''
::-webkit-scrollbar {{ width: 12px; height: 12px; }}
::-webkit-scrollbar-track {{ background: var(--rs-bg); }}
::-webkit-scrollbar-thumb {{
  background: var(--rs-border);
  border-radius: 6px;
}}
::-webkit-scrollbar-thumb:hover {{ background: var(--rs-text-muted); }}
'''}
/* Уведомления */
.q-notification {{
  background: var(--rs-surface) !important;
  color: var(--rs-text) !important;
  border: 1px solid var(--rs-border);
}}"""
