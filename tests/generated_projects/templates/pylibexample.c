// SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
// SPDX-License-Identifier: Apache-2.0

#define PY_SSIZE_T_CLEAN
#include <Python.h>
{% for prefix in prefixes %}
#include <{{ prefix }}example.h>
{% endfor %}

{% for prefix in prefixes %}
static PyObject *{{ prefix }}square_wrapper(PyObject *self, PyObject *args) {
  float input;
  if (!PyArg_ParseTuple(args, "f", &input)) {
    return NULL;
  }
  return PyFloat_FromDouble({{ prefix }}square(input));
}
{% endfor %}

static PyMethodDef {{ package_name }}_methods[] = {
{% for prefix in prefixes %}
    {"{{ prefix }}square", {{ prefix }}square_wrapper, METH_VARARGS, "Square function"},
{% endfor %}
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef {{ package_name }}_module = {PyModuleDef_HEAD_INIT, "{{ package_name }}",
                                             NULL, -1, {{ package_name }}_methods};

PyMODINIT_FUNC PyInit_{{ package_name }}(void) {
  return PyModule_Create(&{{ package_name }}_module);
}
