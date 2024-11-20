"""The implementation of consumer-side loading."""

import importlib


def load_library_module(module_name: str) -> None:
    """Load the specified module, if it exists.

    The function allows the module to not exist so that it may be used by a consumer in
    non-pip contexts (for example, if the library is instead installed by some other
    package manager and so no wheel exists).
    """
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        pass
    else:
        module.loader.load()
        del module
