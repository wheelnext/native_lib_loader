#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <foo.h>

static PyObject *square_wrapper(PyObject *self, PyObject *args) {
  float input;
  if (!PyArg_ParseTuple(args, "f", &input)) {
    return NULL;
  }
  return PyFloat_FromDouble(square(input));
}

static PyMethodDef pylibfoo_methods[] = {
    {"square", square_wrapper, METH_VARARGS, "Square function"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef pylibfoo_module = {PyModuleDef_HEAD_INIT, "pylibfoo",
                                             NULL, -1, pylibfoo_methods};

PyMODINIT_FUNC PyInit_pylibfoo(void) {
  return PyModule_Create(&pylibfoo_module);
}
