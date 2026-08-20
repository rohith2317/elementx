"""
main.py
Entry point for ELEMENTX: AI Gesture Battle.

Run with:
    python main.py

See README.md for setup instructions.
"""
from __future__ import annotations

import sys
import traceback


def main() -> int:
    try:
        from game.game import GameController
    except ImportError as exc:
        print("Failed to import game modules.")
        print(f"Details: {exc}")
        print("Make sure you've installed dependencies with:")
        print("    pip install -r requirements.txt")
        return 1

    try:
        controller = GameController()
        controller.run()
        return 0
    except Exception:
        print("ELEMENTX crashed with an unhandled exception:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
