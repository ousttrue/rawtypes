# rawtypes

`python extension` のコード生成に関するノート。

<https://docs.python.org/3/extending/extending.html>

* python module(`xxx.py` を import すること)
* python package(`xxx/__init__.py` を import すること)
* python extension(ネイティブモジュールを指す。`xxx.pyd`)


## PyCFunction

extension に登録する関数のシグネチャーは以下の通り。

```c++
static PyObject *EXPORT_FUNC(PyObject *self, PyObject *args);
```

### すべて同じパターンでラップされる

1. python の引数を ローカル変数(PyObject*)に展開する
2. ローカル変数に展開した変数から、`C` の値を取り出してローカル変数に展開する。必要であれば、引数のデフォルト値をここで割り当てる。
3. `C` の関数を呼び出す。
4. 返り値が `void` の場合は、 `None` を返す。
5. 返り値をローカル変数に入れる
6. `C` の値から `PyObject` を作って返す。

### 例

```c++
// 例
static PyObject *imgui_Begin(PyObject *self, PyObject *args){
  // 1.
  // CStringType: const char *
  PyObject *t0 = NULL;
  // PointerType: bool*
  PyObject *t1 = NULL;
  // Int32Type: int
  PyObject *t2 = NULL;
  if(!PyArg_ParseTuple(args, "O|OO", &t0, &t1, &t2)) return NULL;
  // 2.
  const char *p0 = get_cstring(t0, nullptr);
  bool *p1 = t1 ? ctypes_get_pointer<bool*>(t1) :  NULL;
  int p2 = t2 ? PyLong_AsLong(t2) :  0;
  // 3. 5.
  auto value = ImGui::Begin(p0, p1, p2);
  // 6.
  PyObject* py_value = (value ? (Py_INCREF(Py_True), Py_True) : (Py_INCREF(Py_False), Py_False));
  return py_value;
}
```

```{toctree}
args
result
```
