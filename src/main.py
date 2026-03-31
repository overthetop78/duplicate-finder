from __future__ import annotations

import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CURRENT_DIR.parent
LOCAL_PACKAGES_DIR = PROJECT_DIR / ".packages"

if str(LOCAL_PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_PACKAGES_DIR))

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from ui.app import launch


if __name__ == "__main__":
    raise SystemExit(launch())
