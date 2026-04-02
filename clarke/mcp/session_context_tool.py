"""Backward-compatible entry point.

Use ``python -m clarke.mcp.server`` instead.
"""

if __name__ == "__main__":
    from clarke.mcp.server import main

    main()
