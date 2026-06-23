"""PyInstaller entry point — use absolute imports (no relative import in __main__)."""

from vectortrack.app import main

if __name__ == "__main__":
    main()
