"""Export the FastAPI contract consumed by the web client."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402

output = ROOT.parent / "frontend" / "openapi.json"
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
