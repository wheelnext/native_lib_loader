"""The implementation of loading for packages that contain a reusable native library."""

from .loader import LibraryLoader, LoadOrder

__all__ = [
    "LibraryLoader",
    "LoadOrder",
]

# To support testing publicly unsupported behaviors of the loader, we replace the
# core library loading object at import time if the environment variable is set.
import os

if "NATIVE_LIB_LOADER_TESTING" in os.environ:
    from ._testing.monkeypatch import monkeypatch

    monkeypatch()
del os
