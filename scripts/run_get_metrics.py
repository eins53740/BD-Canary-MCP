#!/usr/bin/env python3
"""Manual smoke check for the get_metrics MCP tool."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from canary_mcp.server import get_metrics  # noqa: E402


def main() -> None:
    result = get_metrics.fn()
    print("=== get_metrics (Prometheus output) ===")
    print(result[:2000])
    print("\n---")
    print(f"Total bytes: {len(result)}")


if __name__ == "__main__":
    main()
