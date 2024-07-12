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

static PyMethodDef pylibexample2_methods[] = {
    {"square", square_wrapper, METH_VARARGS, "Square function"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef pylibexample2_module = {PyModuleDef_HEAD_INIT, "pylibexample2",
                                             NULL, -1, pylibexample2_methods};

PyMODINIT_FUNC PyInit_pylibexample2(void) {
  return PyModule_Create(&pylibexample2_module);
}
