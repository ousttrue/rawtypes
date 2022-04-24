# setup.py

* pip は Python 3.4 以降では Python 本体に同梱
* (2013)distribute は setuptools にマージされた

* <https://docs.python.org/ja/3/distutils/examples.html>
* (2019)<https://engineer.recruit-lifestyle.co.jp/techblog/2019-12-25-python-packaging-specs/>

## setuptools と distutils

`setuptools.setup` と `distutils.core.setup` はだいたい同じ。

```python
def setup(**attrs):
    # Make sure we have any requirements needed to interpret 'attrs'.
    _install_setup_requires(attrs)
    return distutils.core.setup(**attrs)
```

`deprecated`

```
from distutils.core import setup
setup(name='foo',
      version='1.0',
      py_modules=['foo'],
      )
```

```{warning}
setup.py:1: DeprecationWarning: The distutils package is deprecated and slated for removal in Python 3.12. Use setuptools or check PEP 632 for potential alternatives
```

`setuptools.setup` を使おう。

```{toctree}
command/index
pypi
metadata
```
