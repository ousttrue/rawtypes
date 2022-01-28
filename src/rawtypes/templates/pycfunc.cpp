// clang-format off
static PyObject *{{func_name}}(PyObject *self, PyObject *args) {
  {{ extract -}}
  if (!PyArg_ParseTuple(args, "{{format}}" {{extract_params}}))
    return NULL;
{{ cpp_from_py -}}
  {{ result -}}
}
// clang-format on
