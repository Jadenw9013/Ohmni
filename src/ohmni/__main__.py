"""Entry point for `python -m ohmni`.

The guard matters: without it, anything that imports `ohmni.__main__` --
including the module-import test in tests/test_architecture.py -- runs the CLI
with whatever argv happens to be around.
"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
