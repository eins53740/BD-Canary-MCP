#!/usr/bin/env python3
"""Manual smoke check for the cleanup_expired_cache MCP tool."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from canary_mcp.server import cleanup_expired_cache  # noqa: E402


def main() -> None:
    result = cleanup_expired_cache.fn()
    print("=== cleanup_expired_cache ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
