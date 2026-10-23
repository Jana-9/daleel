"""Write the OpenAPI schema to frontend/openapi.json.

Run from backend/:  uv run python -m scripts.export_openapi
"""

import json
from pathlib import Path

from app.main import app

target = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"
target.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {target}")
