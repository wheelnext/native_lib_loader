import native_lib_loader
import os

loader = native_lib_loader.library.LibraryLoader(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"),
    "{{ library_name }}",
    native_lib_loader.library.LoadMode.{{ load_mode }},
)

__all__ = [
    "loader",
]
