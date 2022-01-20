# sdist

```py
sub_commands = [('check', checking_metadata)]
```

<https://docs.python.org/ja/3/distutils/sourcedist.html>

```
python setup.py sdist --formats=gztar
# => dist/foo-1.0.tar.gz
```

`MANIFEST.in` で中身を制御。

* <https://packaging.python.org/en/latest/guides/using-manifest-in/>

## subcommand check

* <https://docs.python.org/ja/3/distutils/examples.html#checking-a-package>

## `sdist/build_ext` する前にコード生成したい

(生成物はバージョン管理しない)

* clang.cindex から生成する `.cpp`
* python / clang.cindex から生成する `.pyi`
