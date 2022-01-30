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

extern const char CTYPES[] = "ctypes";
extern const char C_VOID_P[] = "c_void_p";
extern const char ADDRESSOF[] = "addressof";
extern const char ARRAY[] = "Array";
extern const char STRUCTURE[] = "Structure";
extern const char POINTER[] = "POINTER";
extern const char _CFUNCPTR[] = "_CFuncPtr";
extern const char VALUE[] = "value";
extern const char CAST[] = "cast";

template <const char *MODULE> PyObject *get() {
  static PyObject *s_module = PyImport_ImportModule(MODULE);
  assert(s_module);
  return s_module;
}

template <const char *MODULE, const char *ATTR> PyObject *get() {
  static PyObject *s_attr = PyObject_GetAttrString(get<MODULE>(), ATTR);
  assert(s_attr);
  return s_attr;
}

template <const char *VALUE> PyObject *str() {
  static PyObject *s_str = PyUnicode_FromString(VALUE);
  assert(s_str);
  return s_str;
}

// static PyObject *s_ctypes_c_void_p = nullptr;
// static PyObject *s_ctypes_addressof = nullptr;
// static PyObject *s_ctypes_Array = nullptr;
// static PyObject *s_ctypes_Structure = nullptr;
// static PyObject *s_ctypes_POINTER = nullptr;
// static PyObject *s_ctypes__CFuncPtr = nullptr;
// static PyObject *s_ctypes_cast = nullptr;
// static PyObject *s_value = nullptr;
// static std::unordered_map<std::string, PyObject *> s_pydear_ctypes;
// static void s_initialize() {
//   if (s_ctypes) {
//     return;
//   }
//   // ctypes
//   s_ctypes = PyImport_ImportModule("ctypes");
//   s_ctypes_c_void_p = PyObject_GetAttrString(s_ctypes, "c_void_p");
//   s_ctypes_addressof = PyObject_GetAttrString(s_ctypes, "addressof");
//   s_ctypes_Array = PyObject_GetAttrString(s_ctypes, "Array");
//   s_ctypes_Structure = PyObject_GetAttrString(s_ctypes, "Structure");
//   s_ctypes_POINTER = PyObject_GetAttrString(s_ctypes, "POINTER");
//   s_ctypes__CFuncPtr = PyObject_GetAttrString(s_ctypes, "_CFuncPtr");
//   s_ctypes_cast = PyObject_GetAttrString(s_ctypes, "cast");
//   //
//   s_value = PyUnicode_FromString("value");
//   //
// }

static void *ctypes_get_addressof(PyObject *src) {
  if (PyObject *p =
          PyObject_CallFunction(get<CTYPES, ADDRESSOF>(), "O", src)) {
    auto pp = PyLong_AsVoidPtr(p);
    Py_DECREF(p);
    return pp;
  }
  return nullptr;
}

template <typename T> T ctypes_get_pointer(PyObject *src) {
  if (!src) {
    return (T) nullptr;
  }

  // ctypes.c_void_p
  if (PyObject_IsInstance(src, get<CTYPES, C_VOID_P>())) {
    if (PyObject *p = PyObject_GetAttr(src, str<VALUE>())) {
      auto pp = PyLong_AsVoidPtr(p);
      Py_DECREF(p);
      return (T)pp;
    }
    PyErr_Clear();
  }

  // ctypes.Array
  // ctypes.Structure
  if (PyObject_IsInstance(src, get<CTYPES, ARRAY>()) ||
      PyObject_IsInstance(src, get<CTYPES, STRUCTURE>()) ||
      PyObject_IsInstance(src, get<CTYPES, _CFUNCPTR>())) {
    if (void *p = ctypes_get_addressof(src)) {
      return (T)p;
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
    static std::unordered_map<std::string, PyObject *> s_pydear_ctypes;
    auto found = s_pydear_ctypes.find(sub);
    if (found == s_pydear_ctypes.end()) {
      p = PyImport_ImportModule((std::string("pydear.") + sub).c_str());
      s_pydear_ctypes.insert(std::make_pair(sub, p));
    } else {
      p = found->second;
    }
  }

  auto T = PyObject_GetAttrString(p, t);
  s_map.insert(std::make_pair(std::string(t), T));
  return T;
}

static PyObject *GetCTypesPointerType(const char *t, const char *sub) {
  static std::unordered_map<std::string, PyObject *> s_map;
  {
    auto found = s_map.find(t);
    if (found != s_map.end()) {
      return found->second;
    }
  }

  auto T = GetCTypesType(t, sub);
  auto result = PyObject_CallFunction(get<CTYPES, POINTER>(), "O", T);
  s_map.insert(std::make_pair(std::string(t), result));
  return result;
}

static PyObject *ctypes_cast(PyObject *src, const char *t, const char *sub) {
  // ctypes.cast(src, ctypes.POINTER(t))[0]
  auto ptype = GetCTypesPointerType(t, sub);
  auto p = PyObject_CallFunction(get<CTYPES, CAST>(), "OO", src, ptype);
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
  return PyObject_CallFunction(get<CTYPES, C_VOID_P>(), "K", (uintptr_t)address);
}

template <typename T>
static PyObject *ctypes_copy(const T &src, const char *t, const char *sub) {
  auto ptype = GetCTypesType(t, sub);
  auto obj = PyObject_CallNoArgs(ptype);
  // get ptr
  auto p = (T *)ctypes_get_addressof(obj);
  // memcpy
  memcpy(p, &src, sizeof(T));
  return obj;
}
