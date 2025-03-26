# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

{% if load_dynamic_lib %}
import shared_lib_consumer
shared_lib_consumer.load_library_module("{{ cpp_package_name }}")
{% endif %}

from . import {{ package_name }}  # noqa: E402

__all__ = ["{{ package_name }}"]
