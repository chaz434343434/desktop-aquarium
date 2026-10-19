import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if os.environ.get("DA_FAULTLOG"):          # testing: write a Python traceback if the game crashes hard
    import faulthandler
    faulthandler.enable(open(os.environ["DA_FAULTLOG"], "w"), all_threads=True)

from purrfin.main import main  # noqa: E402

main(sys.argv[1:])
