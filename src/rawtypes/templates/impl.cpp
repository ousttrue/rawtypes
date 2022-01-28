// generated
#define PY_SSIZE_T_CLEAN
#ifdef _DEBUG
#undef _DEBUG
#include <Python.h>
#define _DEBUG
#include <iostream>
#else
#include <Python.h>
#endif

#include <string>
#include <string_view>
#include <unordered_map>

static PyObject *s_ctypes = nullptr;
static PyObject *s_ctypes_c_void_p = nullptr;
static PyObject *s_ctypes_addressof = nullptr;
static PyObject *s_ctypes_Array = nullptr;
static PyObject *s_ctypes_Structure = nullptr;
static PyObject *s_ctypes_POINTER = nullptr;
static PyObject *s_ctypes__CFuncPtr = nullptr;
static PyObject *s_ctypes_cast = nullptr;
static PyObject *s_value = nullptr;
static std::unordered_map<std::string, PyObject *> s_pydear_ctypes;
static void s_initialize() {
  if (s_ctypes) {
    return;
  }
  // ctypes
  s_ctypes = PyImport_ImportModule("ctypes");
  s_ctypes_c_void_p = PyObject_GetAttrString(s_ctypes, "c_void_p");
  s_ctypes_addressof = PyObject_GetAttrString(s_ctypes, "addressof");
  s_ctypes_Array = PyObject_GetAttrString(s_ctypes, "Array");
  s_ctypes_Structure = PyObject_GetAttrString(s_ctypes, "Structure");
  s_ctypes_POINTER = PyObject_GetAttrString(s_ctypes, "POINTER");
  s_ctypes__CFuncPtr = PyObject_GetAttrString(s_ctypes, "_CFuncPtr");
  s_ctypes_cast = PyObject_GetAttrString(s_ctypes, "cast");
  //
  s_value = PyUnicode_FromString("value");
  //
}

template <typename T> T ctypes_get_pointer(PyObject *src) {
  if (!src) {
    return (T) nullptr;
  }

  // ctypes.c_void_p
  if (PyObject_IsInstance(src, s_ctypes_c_void_p)) {
    if (PyObject *p = PyObject_GetAttr(src, s_value)) {
      auto pp = PyLong_AsVoidPtr(p);
      Py_DECREF(p);
      return (T)pp;
    }
    PyErr_Clear();
  }

  // ctypes.Array
  // ctypes.Structure
  if (PyObject_IsInstance(src, s_ctypes_Array) ||
      PyObject_IsInstance(src, s_ctypes_Structure) ||
      PyObject_IsInstance(src, s_ctypes__CFuncPtr)) {
    if (PyObject *p = PyObject_CallFunction(s_ctypes_addressof, "O", src)) {
      auto pp = PyLong_AsVoidPtr(p);
      Py_DECREF(p);
      return (T)pp;
    }
    PyErr_Print();
    PyErr_Clear();
  }

  return (T) nullptr;
}

static PyObject *GetCTypesType(const char *t, const char *sub) {
  static std::unordered_map<std::string, PyObject *> s_map;
  {
    auto found = s_map.find(t);
    if (found != s_map.end()) {
      return found->second;
    }
  }

  PyObject *p = nullptr;
  {
    auto found = s_pydear_ctypes.find(sub);
    if (found == s_pydear_ctypes.end()) {
      p = PyImport_ImportModule((std::string("pydear.") + sub).c_str());
      s_pydear_ctypes.insert(std::make_pair(sub, p));
    } else {
      p = found->second;
    }
  }

  auto T = PyObject_GetAttrString(p, t);
  auto result = PyObject_CallFunction(s_ctypes_POINTER, "O", T);
  s_map.insert(std::make_pair(std::string(t), result));
  return result;
}

static PyObject *ctypes_cast(PyObject *src, const char *t, const char *sub) {
  // ctypes.cast(src, ctypes.POINTER(t))[0]
  auto ptype = GetCTypesType(t, sub);
  auto p = PyObject_CallFunction(s_ctypes_cast, "OO", src, ptype);
  Py_DECREF(src);
  auto py_value = PySequence_GetItem(p, 0);
  Py_DECREF(p);
  return py_value;
}

static const char *get_cstring(PyObject *src, const char *default_value) {
  if (src) {
    if (auto p = PyUnicode_AsUTF8(src)) {
      return p;
    }
    PyErr_Clear();

    if (auto p = PyBytes_AsString(src)) {
      return p;
    }
    PyErr_Clear();
  }

  return default_value;
}

static PyObject *py_string(const std::string_view &src) {
  return PyUnicode_FromStringAndSize(src.data(), src.size());
}

static PyObject *c_void_p(const void *address) {
  return PyObject_CallFunction(s_ctypes_c_void_p, "K", (uintptr_t)address);
}

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

  s_initialize();

  return __root__;
}
