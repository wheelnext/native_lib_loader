// SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
// SPDX-License-Identifier: Apache-2.0

int square(int x);

int power_four(int x) {
    return square(x) * square(x);
}
