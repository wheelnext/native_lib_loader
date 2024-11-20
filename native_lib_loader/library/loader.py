"""The implementation of loading for packages that contain a reusable native library."""

import ctypes
import os
import platform
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

    def __init__(
        self,
        path_to_local_lib: PathLike,
        lib_name: str,
    ):
        self._path = path_to_local_lib
        self._lib = lib_name
        self._ext = (
            "dll"
            if platform.system() == "Windows"
            else "dylib"
            if platform.system() == "Darwin"
            else "so"
        )
        self._prefix = "" if platform.system() == "Windows" else "lib"
        self._full_lib_name = f"{self._prefix}{self._lib}.{self._ext}"

    def _load_internal(self) -> None:
        """Load the native library in the package."""
        ctypes.CDLL(
            str(Path(self._path) / self._full_lib_name),
            mode=ctypes.RTLD_LOCAL,
        )

    def load(self, *, prefer_system: bool = False) -> None:
        """Load the native library and return the ctypes.CDLL object.

        Parameters
        ----------
        prefer_system : bool
            Whether or not to try loading a system library before the local version.

        """
        # Always load the library in local mode.
        mode = ctypes.RTLD_LOCAL
        if prefer_system or os.getenv(
            f"PREFER_{self._lib.upper()}_SYSTEM_LIBRARY", "false"
        ).lower() not in ("false", 0):
            try:
                ctypes.CDLL(self._full_lib_name, mode)
            except OSError:
                self._load_internal()
        else:
            self._load_internal()
