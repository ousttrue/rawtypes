// generated
#include "rawtypes.h"

// clang-format off
{% for header in headers -%}
{{ header }}
{% endfor -%} // clang-format on

PyMODINIT_FUNC
PyInit_impl(void) {
#ifdef _DEBUG
  std::cout << "DEBUG_BUILD sizeof: ImGuiIO: " << sizeof(ImGuiIO) << std::endl;
#endif

  auto __dict__ = PyImport_GetModuleDict();
  PyObject *__root__ = nullptr;
  { // create empty root module
    static PyMethodDef Methods[] = {
        {NULL, NULL, 0, NULL} /* Sentinel */
    };

    static struct PyModuleDef module = {
        PyModuleDef_HEAD_INIT, "impl", /* name of module */
        nullptr,                       /* module documentation, may be NULL */
        -1, /* size of per-interpreter state of the module,
              or -1 if the module keeps state in global variables. */
        Methods};

    __root__ = PyModule_Create(&module);
    if (!__root__) {
      return NULL;
    }
  }

  // clang-format off
  {% for module in modules -%}
  {{ module }}
  {% endfor -%}
  // clang-format on

  static auto ImplError = PyErr_NewException("impl.error", NULL, NULL);
  Py_XINCREF(ImplError);
  if (PyModule_AddObject(__root__, "error", ImplError) < 0) {
    Py_XDECREF(ImplError);
    Py_CLEAR(ImplError);
    Py_DECREF(__root__);
    return NULL;
  }

  return __root__;
}
