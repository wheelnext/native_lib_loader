"""The implementation of loading for packages that contain a reusable native library."""

import ctypes
from enum import Enum, auto
from os import PathLike
from pathlib import Path


class LoadMode(Enum):
    """Enumeration of the load modes for a library."""

    LOCAL = auto()
    GLOBAL = auto()


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

    """

    def __init__(
        self,
        path_to_local_lib: PathLike,
        lib_name: str,
        mode: LoadMode = LoadMode.GLOBAL,
    ):
        self._path = path_to_local_lib
        self._lib = lib_name
        self._mode = (
            ctypes.RTLD_GLOBAL if mode == LoadMode.GLOBAL else ctypes.RTLD_LOCAL
        )

    def load(self) -> ctypes.CDLL:
        """Load the native library and return the ctypes.CDLL object."""
        # Try system library path first, then try the local path in the wheel.
        try:
            lib = ctypes.CDLL(self._lib, self._mode)
        except OSError:
            lib = ctypes.CDLL(
                str(Path(self._path) / self._lib),
                mode=self._mode,
            )

        return lib
