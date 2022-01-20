from typing import NamedTuple, List, Optional, Callable
from ..clang import cindex


class Unsaved(NamedTuple):
    name: str
    content: str


def get_tu(entrypoint: str,
           *,
           include_dirs: List[str] = None,
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
    if flags:
        arguments.extend(flags)

    # path of libclang.dll
    cindex.Config.library_path = 'C:\\Program Files\\LLVM\\bin'

    index = cindex.Index.create()

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
