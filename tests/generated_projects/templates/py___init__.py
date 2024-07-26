import native_lib_loader

native_lib_loader.consumer.load_library_module("lib{{ project_name }}")

from . import pylib{{ project_name }}

__all__ = ["pylib{{ project_name }}"]
