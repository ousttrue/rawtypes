# metadata

* <https://docs.python.org/3/distutils/setupscript.html#meta-data>
* <https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/#setup-args>

要するに pypi のサイトにどのように反映されるのか知りたい。

## header etc
### project_name

* https://pypi.org/project/rawtypes/

### version

<https://github.com/pypa/setuptools_scm/>

git のタグからバージョンを付ける。

```py
setup(
    use_scm_version=True,
    setup_requires=['setuptools_scm']
)
```

setup.py で pypi にアップロードする際にコード生成してる？

### description

## side

### author
### author_email
### url

project_urls

<https://github.com/pallets/flask/blob/main/setup.cfg>

### license
### classifiers

<https://pypi.org/classifiers/>

## main

### long description

`README.md`

```py
from setuptools import setup

# read the contents of your README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='an_example_package',
    # other arguments omitted
    long_description=long_description,
    long_description_content_type='text/markdown'
)
```
