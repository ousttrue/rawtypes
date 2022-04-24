import setuptools
import pathlib
import os
import platform
HERE = pathlib.Path(__file__).absolute().parent
CLANG_SRC = HERE / 'src/rawtypes/clang/__init__.py'
CLANG_PYTHON_BASE_URL = 'https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-13.0.0/clang/bindings/python/clang/'


if 'LLVM_PATH' in os.environ:
    CLANG_HEADER = pathlib.Path(
        os.environ['LLVM_PATH']) / 'include/clang-c/Index.h'
elif os.name == 'nt':
    CLANG_HEADER = pathlib.Path(
        'C:/Program Files/LLVM/include/clang-c/Index.h')
elif platform.system() == 'Linux':
    # ubuntu: libclang-13-dev
    CLANG_HEADER = pathlib.Path('/usr/lib/llvm-13/include/clang-c/Index.h')


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
    sys.path.append(str(HERE / 'src'))
    from rawtypes.clang_util import generate_cindex_stub
    generate_cindex_stub.generate(
        CLANG_HEADER,
        CLANG_SRC.parent / 'cindex.pyi')


if not CLANG_SRC.exists():
    download_clang_cindex()


setuptools.setup(name='rawtypes',
                 use_scm_version=True,
                 setup_requires=['setuptools_scm'],
                 # package
                 package_dir={'': 'src'},
                 packages=setuptools.find_packages("src"),
                 package_data={'rawtypes.generator': ['templates/*']},
                 install_requires=["Jinja2"],
                 # meta-data
                 description='A code generator using libclang for a python extension.',
                 long_description=(HERE / 'README.md').read_text(),
                 long_description_content_type='text/markdown',
                 author='ousttrue',
                 project_urls={
                     'Documentation': 'https://ousttrue.github.io/rawtypes/',
                     'Source': 'https://github.com/ousttrue/rawtypes',
                 },
                 classifiers=[
                     'Development Status :: 3 - Alpha',
                     'Intended Audience :: Developers',
                     'Topic :: Software Development :: Build Tools',
                     'License :: OSI Approved :: MIT License',
                     'Programming Language :: Python :: 3.10',
                 ]
                 )
