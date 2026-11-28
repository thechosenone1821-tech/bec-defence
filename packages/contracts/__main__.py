"""CLI for shared config pins: python -m packages.contracts [--write]."""
from .config import main

if __name__ == "__main__":
    raise SystemExit(main())
