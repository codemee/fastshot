"""FShot screenshot utility."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("fshot")
except PackageNotFoundError:  # pragma: no cover - only for uninstalled source trees
    __version__ = "unknown"
