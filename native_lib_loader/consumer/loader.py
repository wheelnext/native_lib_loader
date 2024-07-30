"""The implementation of consumer-side loading."""

import importlib


def load_library_module(module_name: str) -> None:
    """Load the specified module, if it exists."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        pass
    else:
        module.loader.load()
        del module
