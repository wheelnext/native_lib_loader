"""The implementation of loading for packages that contain a reusable native library."""

import ctypes
import os
import platform
from enum import Enum, auto
from os import PathLike
from pathlib import Path


class LoadMode(Enum):
    """Mode of the dynamic loader to use when loading the library."""

    LOCAL = auto()
    GLOBAL = auto()
    ENV = auto()


class LoadOrder(Enum):
    """Order in which system vs. package-local libraries should be loaded."""

    ALLOW_SYSTEM = auto()
    REQUIRE_LOCAL = auto()


class LibraryLoader:
    """Container of loading logic for a native library associated with a module.

    Parameters
    ----------
    path_to_local_lib : PathLike
        The path to the local library in the wheel.
    lib_name : str
        The name of the library to load
    mode : LoadMode
        The load mode for the library. Loading globally makes the library's symbols
        available for resolution to all subsequently loaded libraries, whereas local
        loading only populates the loader's list of loaded libraries without polluting
        the symbol table.
    load_order : LoadOrder
        Whether or not to try loading a system library before the local version.

    """

    def __init__(
        self,
        path_to_local_lib: PathLike,
        lib_name: str,
        order: LoadOrder = LoadOrder.ALLOW_SYSTEM,
        mode: LoadMode = LoadMode.GLOBAL,
    ):
        self._path = path_to_local_lib
        self._lib = lib_name
        self._mode = mode
        self._order = order
        self._ext = (
            "dll"
            if platform.system() == "Windows"
            else "dylib"
            if platform.system() == "Darwin"
            else "so"
        )
        self._prefix = "" if platform.system() == "Windows" else "lib"
        self._full_lib_name = f"{self._prefix}{self._lib}.{self._ext}"

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
            mode = (
                ctypes.RTLD_GLOBAL
                if self._mode == LoadMode.GLOBAL
                else ctypes.RTLD_LOCAL
            )
            if self._order == LoadOrder.ALLOW_SYSTEM:
                try:
                    ctypes.CDLL(self._full_lib_name, mode)
                except OSError:
                    ctypes.CDLL(
                        str(Path(self._path) / self._full_lib_name),
                        mode=mode,
                    )
