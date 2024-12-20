"""The implementation of loading for packages that contain a reusable native library."""

from __future__ import annotations

import ctypes
import os
import platform
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Iterable


class PlatformLibrary(NamedTuple):
    """A tuple containing the paths to a library on different platforms.

    Parameters
    ----------
    Linux : Path
        The path to the library on Linux.
    Darwin : Path
        The path to the library on macOS.
    Windows : Path
        The path to the library on Windows.

    """

    Linux: Path | None = None
    Darwin: Path | None = None
    Windows: Path | None = None


class LibraryLoader:
    """Loader for a set of native libraries associated with a module.

    Parameters
    ----------
    libraries : dict[str, PlatformLibrary | tuple[PathLike | str, PathLike | str, PathLike | str]]
        A mapping from library names to the paths of the libraries on each platform. If
        a tuple is passed, it must be ordered as (Linux, Darwin, Windows).

    """  # noqa: E501

    def __init__(
        self,
        libraries: dict[
            str, PlatformLibrary | tuple[PathLike | str, PathLike | str, PathLike | str]
        ],
    ):
        platform_name = platform.system()

        self._libraries = {}
        for lib, path in libraries.items():
            if isinstance(path, tuple):
                path = PlatformLibrary(*(Path(p) for p in path))  # noqa: PLW2901
            if not isinstance(path, PlatformLibrary):
                msg = (
                    f"Invalid path {path} for library {lib}. Expected a tuple or "
                    "PlatformLibrary."
                )
                raise TypeError(msg)

            try:
                self._libraries[lib] = getattr(path, platform_name)
            except AttributeError:
                msg = (
                    f"No library {lib} found for the current platform {platform_name}. "
                    f"This is a bug in the wheel, please report to the maintainer."
                )
                raise ValueError(msg) from None

    @staticmethod
    def _load(library_path: Path | str) -> None:
        """Load the library at the given path with RTLD_LOCAL."""
        ctypes.CDLL(str(library_path), mode=ctypes.RTLD_LOCAL)

    def load(
        self, libraries: Iterable[str] | None = None, *, prefer_system: bool = False
    ) -> None:
        """Load the native library and return the ctypes.CDLL object.

        Parameters
        ----------
        libraries : Iterable[str] | None, optional
            The names of the libraries to load. If None, all libraries are loaded.
        prefer_system : bool, optional
            Whether or not to try loading a system library before the local version.
            Default is False.

        """
        # Always load the library in local mode.

        if libraries is None:
            libraries = self._libraries.keys()

        for library_name in libraries:
            try:
                library_path = self._libraries[library_name]
            except KeyError:
                msg = f"Library {library_name} not found in the package."
                raise ValueError(msg) from None
            if prefer_system or os.getenv(
                f"PREFER_{library_name.upper()}_SYSTEM_LIBRARY", "false"
            ).lower() not in ("false", 0):
                try:
                    self._load(library_path.name)
                except OSError:
                    self._load(library_path)
            else:
                self._load(library_path)
