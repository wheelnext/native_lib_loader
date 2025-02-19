// SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
// SPDX-License-Identifier: Apache-2.0

#include "{{ prefix }}example.h"

int {{ prefix }}square(int x) {
  {% if square_as_cube %}
    return x * x * x;
  {% else %}
    return x * x;
  {% endif %}
}
