#!/usr/bin/env python3
"""
Helper script to update the CANARY_API_TOKEN in .env file.
Usage: python update_api_token.py <your-token-here>
"""

import sys
from pathlib import Path


def update_api_token(token: str) -> bool:
    """Update CANARY_API_TOKEN in .env file."""
    env_file = Path(__file__).parent / ".env"

    if not env_file.exists():
        print(f"Error: .env file not found at {env_file}")
        return False

    # Read current content
    content = env_file.read_text(encoding="utf-8")

    # Replace the token line
    lines = content.split("\n")
    updated = False

    for i, line in enumerate(lines):
        if line.startswith("CANARY_API_TOKEN="):
            old_value = line
            lines[i] = f"CANARY_API_TOKEN={token}"
            updated = True
            print("Updated token:")
            print(f"  Old: {old_value}")
            print(f"  New: CANARY_API_TOKEN={token[:10]}...{token[-5:]}")
            break

    if not updated:
        print("Error: CANARY_API_TOKEN line not found in .env")
        return False

    # Write updated content
    env_file.write_text("\n".join(lines), encoding="utf-8")
    print("\n[OK] .env file updated successfully!")
    print("\nNext steps:")
    print("  1. Restart Claude Desktop (close completely and reopen)")
    print("  2. The MCP server should now connect successfully")
    print("  3. Try asking Claude to 'Use get_server_info to check Canary connection'")

    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_api_token.py <your-token-here>")
        print("\nExample:")
        print("  python update_api_token.py abc123def456...")
        sys.exit(1)

    token = sys.argv[1].strip()

    if not token or token == "your-token-here":
        print("Error: Please provide a valid API token")
        print("The token 'your-token-here' is just a placeholder")
        sys.exit(1)

    if len(token) < 10:
        print("Warning: Token seems very short. Are you sure this is correct?")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    success = update_api_token(token)
    sys.exit(0 if success else 1)
