import native_lib_loader

native_lib_loader.consumer.load_library_module("libexample1")

from . import pylibexample1  # noqa: E402

__all__ = ["pylibexample1"]
