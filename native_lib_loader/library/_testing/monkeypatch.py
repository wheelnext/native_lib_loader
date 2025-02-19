# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Set of patches for testing unsupported versions of library loading.

The versions of library loading that this module adds support for are either
intrinsically dangerous or simply nonfunctional. The primary purpose of this module is
to enable testing of those approaches without exposing them via the public API.
"""

from __future__ import annotations

import ctypes
import os
import platform
from enum import Enum, auto
from os import PathLike
from typing import TYPE_CHECKING

from native_lib_loader import library

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


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
        libraries: dict[
            str,
            library.PlatformLibrary
            | tuple[PathLike | str, PathLike | str, PathLike | str],
        ],
        *,
        mode: LoadMode = LoadMode.GLOBAL,
    ):
        super().__init__(libraries)
        self._mode = mode

    @staticmethod
    def _load_global(library_path: Path | str) -> None:
        """Load the library at the given path with RTLD_GLOBAL."""
        ctypes.CDLL(str(library_path), mode=ctypes.RTLD_GLOBAL)

    def load(
        self, libraries: Iterable[str] | None = None, *, prefer_system: bool = False
    ) -> None:
        """Load the native library and return the ctypes.CDLL object.

        Parameters
        ----------
        libraries : Iterable[str] | None, optional
            The names of the libraries to load. If None, all libraries are loaded.
        prefer_system : bool
            Whether or not to try loading a system library before the local version.

        """
        if self._mode == LoadMode.ENV:
            # Set up env and return.
            env_var = (
                "LD_LIBRARY_PATH"
                if platform.system() == "Linux"
                else "DYLD_LIBRARY_PATH"
                if platform.system() == "Darwin"
                else "PATH"
            )
            sep = ";" if platform.system() == "Windows" else ":"
            if base := os.getenv(env_var, ""):
                base += sep
            os.environ[env_var] = base + sep.join(
                str(path.parent) for path in self._libraries.values()
            )
        else:
            if self._mode == LoadMode.GLOBAL:
                self._load = self._load_global  # type: ignore[method-assign]
            try:
                super().load(libraries, prefer_system=prefer_system)
            finally:
                # Note that the order of the comments here is important because ruff
                # recognizes the noqa after the type comment while mypy does not detect
                # the reverse.
                self._load = library.LibraryLoader._load  # type: ignore[method-assign] # noqa: SLF001


def monkeypatch() -> None:
    """Replace the loader with the testing loader and add loading mode support."""
    library.LibraryLoader = TestingLibraryLoader  # type: ignore[misc, assignment]
    library.LoadMode = LoadMode  # type: ignore[attr-defined]
