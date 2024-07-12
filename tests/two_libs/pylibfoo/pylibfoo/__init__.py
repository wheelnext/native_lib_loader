import native_lib_loader

native_lib_loader.consumer.load_library_module("libfoo")

from . import pylibfoo

__all__ = ["pylibfoo"]
