"""Allow ``python -m proofsentinel``."""

import sys

from proofsentinel.cli import main

if __name__ == "__main__":
    sys.exit(main())