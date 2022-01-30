# 関数の実行と戻り値

## 関数の実行

ローカル変数に展開した引数で関数を呼び出す。

```c++
  auto value = ImGui::Begin(p0, p1, p2);
```

## void

戻り値が無い関数は、 `Py_None` を返す。
`NULL` を返すと例外が起こったことを意味する。

```c++
static PyObject *imgui_End(PyObject *self, PyObject *args){
  if(!PyArg_ParseTuple(args, "")) return NULL;
  ImGui::End();
  Py_INCREF(Py_None);        
  return Py_None;
}
```

## 戻り値 (void以外)

c++ の値を `PyObject*` に変換して返す。

```c++
  PyObject* py_value = (value ? (Py_INCREF(Py_True), Py_True) : (Py_INCREF(Py_False), Py_False));
  return py_value;
```

## Py_INCREF

`PyObject*` の参照カウントをインクリメントする。
`Py_None`, `Py_True`, `Py_False` だけ特殊で自前でインクリメントする。
それ以外(おそらく関数の返り値として入手する)は、手に入った時点で `Py_INCREF` されているようなので、自分でやる必要は無い。
逆に、使い終わったら `Py_DECREF` で参照を減らしてやる必要がある。

## Py_DECREF

`Py_DECREF` の要不要は関数によって違うので逐一調べるしかない。
必要ない感数は `borrow(借用)` と呼称しているようで、`PyArg_ParseTuple` は `借用` らしい。

```c++
// 例
    // ctypes.c_void_p
    if(PyObject_IsInstance(src, s_ctypes_c_void_p)){
        if(PyObject *p = PyObject_GetAttr(src, s_value))
        {
            auto pp = PyLong_AsVoidPtr(p);
            Py_DECREF(p);
            return (T)pp;
        }
        PyErr_Clear();
    }
```

実行時に タスクマネージャーでメモリリークが無いことを確認するとよい。
