import os

import native_lib_loader

loader = native_lib_loader.library.LibraryLoader(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"),
    "libexample.so",
)

__all__ = [
    "loader",
]
