"""Set of patches for testing unsupported versions of library loading.

The versions of library loading that this module adds support for are either
intrinsically dangerous or simply nonfunctional. The primary purpose of this module is
to enable testing of those approaches without exposing them via the public API.
"""

import ctypes
import os
import platform
from enum import Enum, auto
from os import PathLike
from pathlib import Path

from native_lib_loader import library


class LoadMode(Enum):
    """Mode of the dynamic loader to use when loading the library."""

    LOCAL = auto()
    GLOBAL = auto()
    ENV = auto()


class TestingLibraryLoader(library.LibraryLoader):
    """Library loader that allows for testing of unsupported library loading methods.

    This loader add support for RTLD_GLOBAL and environment variable-based loading,
    neither of which is intended for general use due to their various flaws.
    """

    def __init__(
        self,
        path_to_local_lib: PathLike,
        lib_name: str,
        order: library.LoadOrder = library.LoadOrder.ALLOW_SYSTEM,
        mode: LoadMode = LoadMode.GLOBAL,
    ):
        super().__init__(path_to_local_lib, lib_name, order)
        self._mode = mode

    def load(self) -> None:
        """Load the native library and return the ctypes.CDLL object."""
        if self._mode == LoadMode.ENV:
            # Set up env and return.
            env_var = (
                "LD_LIBRARY_PATH"
                if platform.system() == "Linux"
                else "DYLD_LIBRARY_PATH"
                if platform.system() == "Darwin"
                else "PATH"
            )
            os.environ[env_var] = str(Path(self._path))
        else:
            ctypes_mode = (
                ctypes.RTLD_GLOBAL
                if self._mode == LoadMode.GLOBAL
                else ctypes.RTLD_LOCAL
            )
            old_cdll = ctypes.CDLL

            # Patch ctypes.CDLL to unconditionally use the desired mode and ignore the
            # one passed by default in the parent loader class.
            def new_cdll(name, mode=None, *args, **kwargs):  # noqa
                return old_cdll(name, ctypes_mode, *args, **kwargs)

            ctypes.CDLL = new_cdll  # type: ignore[misc,assignment]
            try:
                super().load()
            finally:
                ctypes.CDLL = old_cdll  # type: ignore[misc]


def monkeypatch() -> None:
    """Replace the loader with the testing loader and add loading mode support."""
    library.LibraryLoader = TestingLibraryLoader  # type: ignore[misc]
    library.LoadMode = LoadMode  # type: ignore[attr-defined]
