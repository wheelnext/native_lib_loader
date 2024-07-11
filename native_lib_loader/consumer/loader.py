import importlib


def load_library_module(module_name):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        pass
    else:
        module.loader.load()
        del module
