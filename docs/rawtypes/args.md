# 引き数

-   <https://docs.python.org/3/c-api/index.html>
    -   <https://docs.python.org/3/c-api/arg.html>
    -   <https://docs.python.org/3/extending/extending.html#extracting-parameters-in-extension-functions>

```c++
static PyObject *EXPORT_FUNC(PyObject *self, PyObject *args);
```

の args を C++ の変数に展開する。

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
```

## N 個の引数を `PyObject*` に展開する。

* `PyArg_ParseTuple` を使って `PyObject*` 型の変数 `p0`, `p1`, `p2` に展開する
* "O|OO": 3つの引き数
    * O: `PyObject*` 型
    * |: より後ろはデフォルト値を持つ省略可能な引き数
    * 省略された引数は `NULL` になるのでデフォルト値を適用すること

p2 は、`O` を `i` にかえることで `PyObject*` を経由せずに直接 `int` 型に取り出すことができるが、コード生成の手抜き。

## N 個の `PyObject*` を `C++` の変数に取り出す(引き数のデフォルト値を考慮)

* p1 のデフォルト値は `NULL`
* p2 のデフォルト値は `0`

この段階で、各引数の複数の型への対応を実装できる。

* `str` と `bytes` の両対応
* `ctypes.Array` と `ctypes.Structure` の両対応
* `Tuple[float, float]` を `ImVec2` に展開する
