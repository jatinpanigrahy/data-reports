"""Module execution entry point for reportgen.

Allows running the package directly via `python -m reportgen`.
"""

import sys
from reportgen.cli import main

if __name__ == "__main__":
    sys.exit(main())
