"""Git-clone shim: lets ``python -m agentest`` run from the repo root without installing.

It points this package at ``src/agentest`` (the real code). Installed copies never see this file.
"""

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parents[1] / "src" / "agentest")]
exec(compile((Path(__path__[0]) / "__init__.py").read_text(), __path__[0] + "/__init__.py", "exec"))
