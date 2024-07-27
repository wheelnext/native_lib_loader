import native_lib_loader

native_lib_loader.consumer.load_library_module("{{ cpp_package_name }}")

from . import {{ package_name }}

__all__ = ["{{ package_name }}"]
