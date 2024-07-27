#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <example.h>

static PyObject *square_wrapper(PyObject *self, PyObject *args) {
  float input;
  if (!PyArg_ParseTuple(args, "f", &input)) {
    return NULL;
  }
  return PyFloat_FromDouble(square(input));
}

static PyMethodDef {{ package_name }}_methods[] = {
    {"square", square_wrapper, METH_VARARGS, "Square function"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef {{ package_name }}_module = {PyModuleDef_HEAD_INIT, "{{ package_name }}",
                                             NULL, -1, {{ package_name }}_methods};

PyMODINIT_FUNC PyInit_{{ package_name }}(void) {
  return PyModule_Create(&{{ package_name }}_module);
}
