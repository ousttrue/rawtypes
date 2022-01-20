# setup.py の拡張

* <https://docs.python.org/ja/3/distutils/extending.html>
* [setuptoolsを使ったインストール時に任意の処理を実行する](https://qiita.com/kokumura/items/c2f3670ee5baebdef86b)
* <https://jichu4n.com/posts/how-to-add-custom-build-steps-and-commands-to-setuppy/>
* [Python: セットアップスクリプト (setup.py) に自作のコマンドを追加する](https://blog.amedama.jp/entry/2015/09/17/224627)

## 新規のコマンド

```py
from distutils.command.build_py import build_py as _build_py
from distutils.core import setup

class build_py(_build_py):
    """Specialized Python source builder."""

    # implement whatever needs to be different...

setup(cmdclass={'build_py': build_py},
      ...)
```

`cmdclass`
