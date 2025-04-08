# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""The implementation of loading for packages that contain a reusable native library."""

from __future__ import annotations

import ctypes
import os
import platform
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from collections.abc import Iterable


# Once we require Python 3.10, switch to using a dataclass with kw_only=True
class PlatformLibrary:
    """A tuple containing the paths to a library on different platforms.

    Parameters
    ----------
    Linux : os.PathLike
        The path to the library on Linux.
    Darwin : os.PathLike
        The path to the library on macOS.
    Windows : os.PathLike
        The path to the library on Windows.
    default : typing.Callable[[], os.PathLike]
        A callable that returns the default path to the library. This is used when the
        current platform is not found in the library paths. It may also be used by
        libraries that require a more general key for determining what path to use if
        the choice needs to be made at runtime based on additional factors.

    """

    Linux: Path | None
    Darwin: Path | None
    Windows: Path | None

    def __init__(
        self,
        *,
        Darwin: os.PathLike | str | None = None,  # noqa: N803
        Linux: os.PathLike | str | None = None,  # noqa: N803
        Windows: os.PathLike | str | None = None,  # noqa: N803
        default: Callable[[], os.PathLike | str] | None = None,
    ):
        # public attributes should correspond to platform.system() return values:
        # https://docs.python.org/3/library/platform.html#platform.system
        # TODO: Determine if sys.platform is more appropriate
        # https://discuss.python.org/t/clarify-usage-of-platform-system/70900/4
        if not all(
            isinstance(path, (os.PathLike, str)) or path is None
            for path in (Darwin, Linux, Windows)
        ):
            raise TypeError("Paths must be instances of pathlib.Path, str, or None.")
        self.Darwin = Path(Darwin) if Darwin else None
        self.Linux = Path(Linux) if Linux else None
        self.Windows = Path(Windows) if Windows else None
        if not all(
            p.is_absolute()
            for p in (self.Darwin, self.Linux, self.Windows)
            if p is not None
        ):
            raise ValueError("All paths must be absolute.")
        self.default = default


class LibraryLoader:
    """Loader for a set of native libraries associated with a module.

    Parameters
    ----------
    libraries : dict[str, PlatformLibrary | tuple[os.PathLike | str, os.PathLike | str, os.PathLike | str]]
        A mapping from library names to the paths of the libraries on each platform. If
        a tuple is passed, it must be ordered as (Linux, Darwin, Windows).

    """  # noqa: E501

    def __init__(
        self,
        libraries: dict[str, PlatformLibrary],
    ):
        platform_name = platform.system()

        self._libraries = {}
        for lib, path in libraries.items():
            if not isinstance(path, PlatformLibrary):
                raise TypeError(
                    f"Invalid path {path} for library {lib}. Expected a tuple or "
                    "PlatformLibrary."
                )

            try:
                self._libraries[lib] = getattr(path, platform_name)
            except AttributeError:
                if path.default is not None:
                    self._libraries[lib] = Path(path.default())
                else:
                    raise ValueError(
                        f"No library {lib} found for the current platform "
                        f"{platform_name}. This is a bug in the wheel, please report "
                        "to the maintainer."
                    ) from None

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
        libraries : typing.Iterable[str] | None
            The names of the libraries to load. If None, all libraries are loaded.
        prefer_system : bool
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
                raise ValueError(
                    f"Library {library_name} not found in the package."
                ) from None
            if prefer_system or os.getenv(
                f"PREFER_{library_name.upper()}_SYSTEM_LIBRARY", "false"
            ).lower() not in ("false", 0):
                try:
                    self._load(library_path.name)
                except OSError:
                    self._load(library_path)
            else:
                self._load(library_path)
