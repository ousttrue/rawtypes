import setuptools
import pathlib
HERE = pathlib.Path(__file__).absolute().parent
CLANG_SRC = HERE / 'src/rawtypes/clang/__init__.py'
CLANG_PYTHON_BASE_URL = 'https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-13.0.0/clang/bindings/python/clang/'


def patch_enum(src):
    return src.replace(
        b'import clang.enumerations', b'from . import enumerations').replace(
            b'clang.enumerations', b'enumerations'
    )


def http_get(url_base: str, dst_dir: pathlib.Path, name: str, patch=None):
    url = url_base + name
    print(url)
    import urllib.request
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        data = res.read()
        if patch:
            data = patch(data)
        (dst_dir / name).write_bytes(data)


def download_clang_cindex():
    '''
    downlod clang package.
    save as `rawtypes.clang`
    '''
    CLANG_SRC.parent.mkdir(parents=True, exist_ok=True)
    http_get(CLANG_PYTHON_BASE_URL, CLANG_SRC.parent, '__init__.py')
    http_get(CLANG_PYTHON_BASE_URL, CLANG_SRC.parent, 'cindex.py', patch_enum)
    http_get(CLANG_PYTHON_BASE_URL, CLANG_SRC.parent, 'enumerations.py')
    # generate typing
    import sys
    sys.path.append(str(HERE))
    from rawtypes.clang_util import generate_cindex_stub
    generate_cindex_stub.generate(
        pathlib.Path('C:/Program Files/LLVM/include/clang-c/Index.h'),
        CLANG_SRC.parent / 'cindex.pyi')


if not CLANG_SRC.exists():
    download_clang_cindex()


setuptools.setup(name='rawtypes',
                 use_scm_version=True,
                 setup_requires=['setuptools_scm'],
                 package_dir={'': 'src'},
                 packages=setuptools.find_packages("src"),
                 long_description=(HERE / 'README.md').read_text(),
                 long_description_content_type='text/markdown'
                 )
