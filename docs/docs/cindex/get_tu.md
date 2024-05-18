# C/C++ のソースをパースして TranslaionUnit を得る

path が parse のエントリポイントとなる。

```{gitinclude} HEAD src/pycindex/get_tu.py
:language: python
```

unsaved file はメモリ上のファイルに仮の名前を与えてパースする仕組み。
エディタで未保存のファイルを対象にする他に、
複数のヘッダーを一度にパースしたい場合に
まとめて include する一時ファイルをメモリ上で済ます用途がある。

```c
// unsaved content
#include "a.h"
#include "b.h"
#include "c.h"
```

## compiler 引数

arguments の与え方で vc の `cl.exe` のようにふるまわせることができる。

* -D による define
* -I による include パス
* c++17 などの対応レベル

などをよく使う。

## flags

* `cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES`

など。関数の中身をスキップする。
言語バインディングの生成をする場合には関数のシグニチャのみが必要。

マクロの制御などもあり、指定しないと出現しない cursor がある。
