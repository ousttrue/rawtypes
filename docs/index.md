# rawtypes

* clang.cindex を用いた c++ バインディングジェネレーター
* clang.cindex を用いた c++ pyi ジェネレーター
* 既存のpythonライブラリに対する pyi ジェネレーター
    * class
    * instance

現状、 `ImGui` のラッパー生成専用。
徐々に、他のこともできるようにしていく。

```{toctree}
:maxdepth: 1
setup/index
cindex/index
examples/index
```

## 関連

* [ClangのPython bindingを使ったC++の関数定義部の特定](https://qiita.com/subaru44k/items/4e69ec987547011d7e63)
* <https://eli.thegreenplace.net/2011/07/03/parsing-c-in-python-with-clang>

* [libclang で 言語バインディングを作る](https://ousttrue.github.io/posts/2021/winter/cindex/)
* [libclang で luajit 向けの FFI を生成する](https://ousttrue.github.io/posts/2021/luajitffi/)

## Indices and tables

-   {ref}`genindex`
-   {ref}`search`