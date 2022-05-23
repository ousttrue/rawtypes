from typing import NamedTuple, List, Optional, Callable
import os
import pathlib
import platform
from ..clang import cindex
import logging
logger = logging.getLogger(__name__)

SO_UBUNTU = pathlib.Path('/usr/lib/x86_64-linux-gnu/libclang-13.so')
SO_GENTOO = pathlib.Path('/usr/lib/llvm/13/lib64/libclang.so.13')


class Unsaved(NamedTuple):
    name: str
    content: str


def get_tu(entrypoint: str,
           *,
           include_dirs: List[str] = [],
           definitions: List[str] = [],
           flags: List[str] = [],
           unsaved: Optional[List[Unsaved]] = None,
           target: str = '') -> cindex.TranslationUnit:
    arguments = [
        "-x",
        "c++",
        "-std=c++17",
    ]
    if target:
        pass
    elif platform.system() == 'Windows':
        target = "x86_64-windows-msvc"

    if platform.system() == 'Windows':
        arguments += [
            "-target",
            target,
            "-fdeclspec",
            "-fms-compatibility-version=18",
            "-fms-compatibility",
            "-DNOMINMAX",
        ]
    else:
        arguments += [
            "-I/usr/lib/clang/13.0.1/include",
        ]
    if include_dirs:
        arguments.extend(f'-I{i}' for i in include_dirs)
    if definitions:
        arguments.extend(f'-D{d}' for d in definitions)
    if flags:
        arguments.extend(flags)

    # path of libclang.dll
    if 'LLVM_PATH' in os.environ:
        # https://github.com/KyleMayes/install-llvm-action
        cindex.Config.library_path = os.environ['LLVM_PATH'] + '/lib'
        cindex.Config.library_file = 'libclang.so'
    elif os.name == 'nt':
        cindex.Config.library_path = 'C:\\Program Files\\LLVM\\bin'
    elif platform.system() == 'Linux':
        if SO_UBUNTU.exists():
            # apt install libclang1-13
            cindex.Config.library_path = str(SO_UBUNTU.parent)
            cindex.Config.library_file = SO_UBUNTU.name
        elif SO_GENTOO.exists():
            cindex.Config.library_path = str(SO_GENTOO.parent)
            cindex.Config.library_file = SO_GENTOO.name

    index = cindex.Index.create()
    logger.debug(arguments)
    tu = index.parse(entrypoint, arguments, unsaved,
                     cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
                     | cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)

    return tu


def _traverse(callback: Callable[[cindex.Cursor], bool], *cursor_path: cindex.Cursor):
    if callback(*cursor_path):
        for child in cursor_path[-1].get_children():
            _traverse(callback, *cursor_path, child)


def traverse(tu: cindex.TranslationUnit, callback: Callable[[cindex.Cursor], bool]):
    for child in tu.cursor.get_children():
        _traverse(callback, child)
