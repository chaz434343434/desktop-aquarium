import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from purrfin.main import main  # noqa: E402

main(sys.argv[1:])
