from typing import NamedTuple, Callable
import pathlib
import os
import logging
import platform
import dataclasses
from ..clang import cindex
from .. import get_cindex

LOGGER = logging.getLogger(__name__)

CINDEX_HEADER = get_cindex.CINDEX_HEADER
SO_UBUNTU = pathlib.Path("/usr/lib/x86_64-linux-gnu/libclang-13.so")
SO_GENTOO = pathlib.Path("/usr/lib/llvm/13/lib64/libclang.so.13")


class Unsaved(NamedTuple):
    name: str
    content: str


def get_tu(
    entrypoint: str | pathlib.Path,
    *,
    include_dirs: list[pathlib.Path] | None = None,
    definitions: list[str] | None = None,
    flags: list[str] | None = None,
    unsaved: list[Unsaved] | None = None,
    target: str = "",
) -> cindex.TranslationUnit:
    arguments = [
        "-x",
        "c++",
        "-std=c++17",
    ]
    if isinstance(entrypoint, pathlib.Path):
        entrypoint = str(entrypoint)

    if target:
        pass
    elif platform.system() == "Windows":
        target = "x86_64-windows-msvc"

    if platform.system() == "Windows":
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
        arguments.extend(f"-I{str(i)}" for i in include_dirs)
    if definitions:
        arguments.extend(f"-D{d}" for d in definitions)
    if flags:
        arguments.extend(flags)

    # path of libclang.dll
    if "LLVM_PATH" in os.environ:
        # https://github.com/KyleMayes/install-llvm-action
        cindex.Config.library_path = os.environ["LLVM_PATH"] + "/lib"  # type: ignore
        cindex.Config.library_file = "libclang.so"  # type: ignore
    elif os.name == "nt":
        cindex.Config.library_path = "C:\\Program Files\\LLVM\\bin"  # type: ignore
    elif platform.system() == "Linux":
        if SO_UBUNTU.exists():
            # apt install libclang1-13
            cindex.Config.library_path = str(SO_UBUNTU.parent)
            cindex.Config.library_file = SO_UBUNTU.name
        elif SO_GENTOO.exists():
            cindex.Config.library_path = str(SO_GENTOO.parent)
            cindex.Config.library_file = SO_GENTOO.name

    index = cindex.Index.create()  # type: ignore
    LOGGER.debug(entrypoint)
    LOGGER.debug(arguments)
    LOGGER.debug(unsaved)
    tu = index.parse(  # type: ignore
        entrypoint,
        arguments,
        unsaved,
        cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        | cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES,
    )

    return tu  # type: ignore


def _traverse(callback: Callable[[cindex.Cursor], bool], *cursor_path: cindex.Cursor):
    if callback(*cursor_path):
        for child in cursor_path[-1].get_children():
            _traverse(callback, *cursor_path, child)


def traverse(tu: cindex.TranslationUnit, callback: Callable[[cindex.Cursor], bool]):
    for child in tu.cursor.get_children():
        _traverse(callback, child)


@dataclasses.dataclass
class Parser:
    entrypoint: str
    tu: cindex.TranslationUnit
    functions: list[tuple[cindex.Cursor, ...]] = dataclasses.field(default_factory=list)
    enums: list[tuple[cindex.Cursor, ...]] = dataclasses.field(default_factory=list)

    @staticmethod
    def create(entrypoint: str) -> "Parser":
        return Parser(entrypoint, get_tu(entrypoint))

    def filter(self, *cursor_path: cindex.Cursor) -> bool:
        cursor = cursor_path[-1]
        location: cindex.SourceLocation = cursor.location
        if not location:
            return False
        if not location.file:
            return False

        if location.file.name == self.entrypoint:
            if cursor.kind == cindex.CursorKind.FUNCTION_DECL:
                self.functions.append(cursor_path)
            elif cursor.kind == cindex.CursorKind.ENUM_DECL:
                self.enums.append(cursor_path)

        return True

    def traverse(self):
        traverse(self.tu, self.filter)
