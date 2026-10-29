"""TNxIDM entry point. --self-test runs headless without PySide6."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    if "--self-test" in sys.argv:
        from tnxidm.selftest import run_selftest
        sys.exit(run_selftest())
    # GUI only from here on; Qt is imported lazily so --self-test stays light.
    try:
        from tnxidm.gui import run_gui
    except ImportError as e:
        print(f"PySide6 is required for the GUI: {e}")
        print("Install it with: pip install -r requirements.txt")
        return 1
    return run_gui()

if __name__ == "__main__":
    sys.exit(main())
