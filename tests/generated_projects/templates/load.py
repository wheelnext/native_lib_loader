# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

import native_lib_loader
import os

root = os.path.dirname(os.path.abspath(__file__))
loader = native_lib_loader.library.LibraryLoader(
    {
# Write a jinja for loop over library_names
{% for library_name in library_names %}
        "{{ library_name }}": native_lib_loader.library.PlatformLibrary(
            Linux=os.path.join(root, "lib", "lib{{ library_name }}.so"),
            Darwin=os.path.join(root, "lib", "lib{{ library_name }}.dylib"),
            Windows=os.path.join(root, "lib", "{{ library_name }}.dll"),
        ),
{% endfor %}
    },
    mode=native_lib_loader.library.LoadMode.{{ load_mode }},
)

__all__ = [
    "loader",
]
