import native_lib_loader

native_lib_loader.consumer.load_library_module("libbar")

from . import pylibbar

__all__ = ["pylibbar"]
