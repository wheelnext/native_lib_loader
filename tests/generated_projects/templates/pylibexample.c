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

static PyMethodDef pylibexample_methods[] = {
    {"square", square_wrapper, METH_VARARGS, "Square function"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef pylibexample_module = {PyModuleDef_HEAD_INIT, "pylibexample",
                                             NULL, -1, pylibexample_methods};

PyMODINIT_FUNC PyInit_pylibexample(void) {
  return PyModule_Create(&pylibexample_module);
}
