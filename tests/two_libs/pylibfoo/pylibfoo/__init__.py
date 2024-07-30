import native_lib_loader

native_lib_loader.consumer.load_library_module("libfoo")

from . import pylibfoo  # noqa: E402

__all__ = ["pylibfoo"]
