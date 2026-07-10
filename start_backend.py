"""Script de arranque simple para levantar el backend de análisis."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CMD = [sys.executable, str(ROOT / "src" / "backend_server.py")]

if __name__ == "__main__":
    env = os.environ.copy()
    env.setdefault("BACKEND_HOST", "0.0.0.0")
    env.setdefault("BACKEND_PORT", "8766")
    subprocess.Popen(CMD, cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    print("Backend iniciado en http://0.0.0.0:8766")
