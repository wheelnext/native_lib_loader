import native_lib_loader

native_lib_loader.consumer.load_library_module("libbar")

from . import pylibbar  # noqa: E402

__all__ = ["pylibbar"]
