"""eli_lab procedural pattern generator.

The package import is preferred, but this module also supports direct execution
from inside the ``pattern_app`` directory for convenience.
"""

try:
    from .generator import PatternConfig, PatternRenderer, RenderResult
except ImportError:  # pragma: no cover - direct ``python __init__.py`` launch
    from generator import PatternConfig, PatternRenderer, RenderResult

__all__ = ["PatternConfig", "PatternRenderer", "RenderResult"]
