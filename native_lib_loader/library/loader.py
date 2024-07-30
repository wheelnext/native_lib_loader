"""The implementation of loading for packages that contain a reusable native library."""

import ctypes
from os import PathLike
from pathlib import Path


class LibraryLoader:
    """Container of loading logic for a native library associated with a module.

    Parameters
    ----------
    path_to_local_lib : PathLike
        The path to the local library in the wheel.
    lib_name : str
        The name of the library to load

    """

    def __init__(self, path_to_local_lib: PathLike, lib_name: str):
        self._path = path_to_local_lib
        self._lib = lib_name

    def load(self) -> ctypes.CDLL:
        """Load the native library and return the ctypes.CDLL object."""
        # Try system library path first, then try the local path in the wheel.
        try:
            lib = ctypes.CDLL(self._lib, ctypes.RTLD_GLOBAL)
        except OSError:
            lib = ctypes.CDLL(
                str(Path(self._path) / self._lib),
                ctypes.RTLD_GLOBAL,
            )

        return lib
