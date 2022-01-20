# build_py

## extend

* <https://docs.python.org/ja/3/distutils/extending.html>

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
