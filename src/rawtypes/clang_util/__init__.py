from typing import NamedTuple, List, Optional, Callable
import os
import platform
from ..clang import cindex
import logging
logger = logging.getLogger(__name__)


class Unsaved(NamedTuple):
    name: str
    content: str


def get_tu(entrypoint: str,
           *,
           include_dirs: List[str] = None,
           definitions: List[str] = None,
           flags: List[str] = None,
           unsaved: Optional[List[Unsaved]] = None) -> cindex.TranslationUnit:
    arguments = [
        "-x",
        "c++",
        "-target",
        "x86_64-windows-msvc",
        "-fms-compatibility-version=18",
        "-fdeclspec",
        "-fms-compatibility",
        "-std=c++17",
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
        # ubuntu
        # apt install libclang1-13
        cindex.Config.library_path = '/usr/lib/x86_64-linux-gnu'
        cindex.Config.library_file = 'libclang-13.so'

    index = cindex.Index.create()
    logger.debug(arguments)
    tu = index.parse(entrypoint, arguments, unsaved,
                     cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD |
                     cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)

    return tu


def _traverse(callback: Callable[[cindex.Cursor], bool], *cursor_path: cindex.Cursor):
    if callback(*cursor_path):
        for child in cursor_path[-1].get_children():
            _traverse(callback, *cursor_path, child)


def traverse(tu: cindex.TranslationUnit, callback: Callable[[cindex.Cursor], bool]):
    for child in tu.cursor.get_children():
        _traverse(callback, child)
