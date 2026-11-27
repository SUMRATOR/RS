from pathlib import Path

root = Path(r"C:\Users\StAlIN\Desktop\rubik-studio")

for path in root.rglob("*.py"):
    if "backups" in path.parts or ".venv" in path.parts:
        continue

    if path.name == "experimental_diagrams_v22.py":
        print("НАЙДЕН ПО ИМЕНИ:", path)
        continue

    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        continue

    if "RS_EXPERIMENTAL_CANVAS_V22" in text:
        print("НАЙДЕН ПО КОДУ:", path)
