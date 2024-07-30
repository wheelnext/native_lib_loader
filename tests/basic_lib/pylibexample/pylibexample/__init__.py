import native_lib_loader

native_lib_loader.consumer.load_library_module("libexample")

from . import pylibexample  # noqa: E402

__all__ = ["pylibexample"]
