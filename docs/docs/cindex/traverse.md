# CXCursor: カーソルを走査する

TranslationUnit.cursor が木構造になっているのでこれを走査する。
なんの木構造なのかというと `C/C++` のソースの namespace の木構造みたいない感じ？
`#include` が展開されるので膨大な数のシンボルが出てくる場合がある。
各カーソルは、型定義や関数定義 `typedef` などの言語要素を指し示す。

例えば、ライブラリの python binding を生成する目的でパーする場合、

* ライブラリの関数を集める(含まれているファイルパスでフィルタし、場合によっては dllexport の有無や命名規則で絞る)
* 集めた関数の引数と返り値が参照する型の情報をすべて集める(enum, struct, typedef)
* マクロは鬼門

という感じ。

```{gitinclude} HEAD src/pycindex/traverse.py
:language: python
```

## 空のソースをパースしてみる

```python
    def test_empty_source(self):
        source = '''
'''
        tu = pycindex.get_tu(
            'tmp.h', unsaved=[pycindex.Unsaved('tmp.h', source)])

        items = {}

        def callback(*cursor_path: cindex.Cursor):
            cursor = cursor_path[-1]
            value = items.get(cursor.kind, 0)
            items[cursor.kind] = value + 1
            return True
        pycindex.traverse(callback, tu)

        for k, v in items.items():
            print(k, v)
```

```
CursorKind.MACRO_DEFINITION 358
```

という結果になった。
