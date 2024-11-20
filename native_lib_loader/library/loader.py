"""The implementation of loading for packages that contain a reusable native library."""

import ctypes
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
    prefer_system : bool
        Whether or not to try loading a system library before the local version.

    """

    def __init__(
        self,
        path_to_local_lib: PathLike,
        lib_name: str,
        *,
        prefer_system: bool = False,
    ):
        self._path = path_to_local_lib
        self._lib = lib_name
        self._prefer_system = prefer_system
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
        # Always load the library in local mode.
        mode = ctypes.RTLD_LOCAL
        if self._prefer_system:
            try:
                ctypes.CDLL(self._full_lib_name, mode)
            except OSError:
                ctypes.CDLL(
                    str(Path(self._path) / self._full_lib_name),
                    mode=mode,
                )
        else:
            ctypes.CDLL(
                str(Path(self._path) / self._lib),
                mode=mode,
            )
