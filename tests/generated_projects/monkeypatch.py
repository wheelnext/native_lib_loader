# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Set of patches for testing unsupported versions of library loading.

The versions of library loading that this module adds support for are either
intrinsically dangerous or simply nonfunctional. The primary purpose of this module is
to enable testing of those approaches without exposing them via the public API.
"""

import ctypes
import os
import platform
from collections.abc import Iterable
from enum import Enum, auto
from pathlib import Path

# Need to disable this because we cannot put `from __future__ import annotations` into
# this file without breaking the interpreter since all of this code is injected into the
# middle of a module instead of the beginning.
# ruff: noqa: FA102


class LoadMode(Enum):
    """Mode of the dynamic loader to use when loading the library."""

    LOCAL = auto()
    GLOBAL = auto()
    ENV = auto()


# Create an alias so we don't lose the original reference after the override.
LibraryLoaderOriginal = LibraryLoader  # type: ignore[misc, used-before-def] # noqa: F821


class TestingLibraryLoader(LibraryLoaderOriginal):
    """Library loader that allows for testing of unsupported library loading methods.

    This loader add support for RTLD_GLOBAL and environment variable-based loading,
    neither of which is intended for general use due to their various flaws.
    """

    def __init__(
        self,
        libraries: dict[str, PlatformLibrary],  # type: ignore[name-defined] # noqa: F821
        *,
        mode: LoadMode = LoadMode.GLOBAL,
    ):
        super().__init__(libraries)
        self._mode = mode

    @staticmethod
    def _load_global(library_path: Path | str) -> None:  # type: ignore[syntax]
        """Load the library at the given path with RTLD_GLOBAL."""
        ctypes.CDLL(str(library_path), mode=ctypes.RTLD_GLOBAL)

    def load(
        self,
        libraries: Iterable[str] | None = None,  # type: ignore[syntax]
        *,
        prefer_system: bool = False,
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
                self._load = LibraryLoaderOriginal._load  # type: ignore[method-assign] # noqa: SLF001


LibraryLoader = TestingLibraryLoader  # type: ignore[misc]
