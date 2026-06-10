#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

if __name__ == "__main__":
    uvicorn.run(
        "financial_mlops.service:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
