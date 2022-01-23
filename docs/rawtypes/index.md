# rawtypes

`python extension` のコード生成に関するノート。

<https://docs.python.org/3/extending/extending.html>

* python module(`xxx.py` を import すること)
* python package(`xxx/__init__.py` を import すること)
* python extension(ネイティブモジュールを指す。`xxx.pyd`)

extension に登録する関数のシグネチャーは以下の通り。

```c++
static PyObject *EXPORT_FUNC(PyObject *self, PyObject *args);
```

```c++
// 例
static PyObject *imgui_Begin(PyObject *self, PyObject *args){
  // CStringType: const char *
  PyObject *t0 = NULL;
  // PointerType: bool*
  PyObject *t1 = NULL;
  // Int32Type: int
  PyObject *t2 = NULL;
  if(!PyArg_ParseTuple(args, "O|OO", &t0, &t1, &t2)) return NULL;
  const char *p0 = get_cstring(t0, nullptr);
  bool *p1 = t1 ? ctypes_get_pointer<bool*>(t1) :  NULL;
  int p2 = t2 ? PyLong_AsLong(t2) :  0;
  auto value = ImGui::Begin(p0, p1, p2);
  PyObject* py_value = (value ? (Py_INCREF(Py_True), Py_True) : (Py_INCREF(Py_False), Py_False));
  return py_value;
}
```

```{toctree}
args
result
```
