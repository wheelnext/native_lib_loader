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

static PyMethodDef pylib{{ project_name }}_methods[] = {
    {"square", square_wrapper, METH_VARARGS, "Square function"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef pylib{{ project_name }}_module = {PyModuleDef_HEAD_INIT, "pylib{{ project_name }}",
                                             NULL, -1, pylib{{ project_name }}_methods};

PyMODINIT_FUNC PyInit_pylib{{ project_name }}(void) {
  return PyModule_Create(&pylib{{ project_name }}_module);
}
