#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <bar.h>

static PyObject *square_wrapper(PyObject *self, PyObject *args) {
  float input;
  if (!PyArg_ParseTuple(args, "f", &input)) {
    return NULL;
  }
  return PyFloat_FromDouble(square(input));
}

static PyMethodDef pylibbar_methods[] = {
    {"square", square_wrapper, METH_VARARGS, "Square function"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef pylibbar_module = {PyModuleDef_HEAD_INIT, "pylibbar",
                                             NULL, -1, pylibbar_methods};

PyMODINIT_FUNC PyInit_pylibbar(void) {
  return PyModule_Create(&pylibbar_module);
}
