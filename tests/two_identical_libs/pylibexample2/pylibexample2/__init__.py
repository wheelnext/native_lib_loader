import native_lib_loader

native_lib_loader.consumer.load_library_module("libexample2")

from . import pylibexample2  # noqa: E402

__all__ = ["pylibexample2"]
