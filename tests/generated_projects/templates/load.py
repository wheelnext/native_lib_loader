import native_lib_loader
import os

root = os.path.dirname(os.path.abspath(__file__))
loader = native_lib_loader.library.LibraryLoader(
    {
        "{{ library_name }}": (
            os.path.join(root, "lib", "lib{{ library_name }}.so"),
            os.path.join(root, "lib", "lib{{ library_name }}.dylib"),
            os.path.join(root, "lib", "{{ library_name }}.dll"),
        )
    },
    mode=native_lib_loader.library.LoadMode.{{ load_mode }},
)

__all__ = [
    "loader",
]
