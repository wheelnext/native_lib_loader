# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""The implementation of consumer-side loading."""

import importlib


def load_library_module(module_name: str, *, prefer_system: bool = False) -> None:
    """Load the specified module, if it exists.

    The function allows the module to not exist so that it may be used by a consumer in
    non-pip contexts (for example, if the library is instead installed by some other
    package manager and so no wheel exists).

    Parameters
    ----------
    module_name : str
        The name of the module to load.
    prefer_system : bool
        Whether or not to try loading a system library before the local version.

    """
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        pass
    else:
        module.loader.load(prefer_system=prefer_system)
        del module
