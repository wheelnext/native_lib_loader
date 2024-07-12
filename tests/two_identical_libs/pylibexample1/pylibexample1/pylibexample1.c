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

static PyMethodDef pylibexample1_methods[] = {
    {"square", square_wrapper, METH_VARARGS, "Square function"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef pylibexample1_module = {PyModuleDef_HEAD_INIT, "pylibexample1",
                                             NULL, -1, pylibexample1_methods};

PyMODINIT_FUNC PyInit_pylibexample1(void) {
  return PyModule_Create(&pylibexample1_module);
}
