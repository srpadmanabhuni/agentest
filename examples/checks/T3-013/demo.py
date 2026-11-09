"""Demo for T3-013. Prints the pass and fail verdicts."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("check_demo", ROOT / "examples" / "checks" / "_demo.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
raise SystemExit(module.main(["T3-013"]))
