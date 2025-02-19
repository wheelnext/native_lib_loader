# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""The library loading logic for consumers of native libraries."""

from .loader import load_library_module

__all__ = ["load_library_module"]
