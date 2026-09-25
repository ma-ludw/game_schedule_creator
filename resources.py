import sys
from pathlib import Path


def resource_path(filename: str) -> Path:
    """Return a resource path that works both from source and PyInstaller builds."""
    bundle_directory = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return Path(bundle_directory) / filename
