from typing import NamedTuple, Callable
import re
import pathlib
import os
import logging
import platform
import dataclasses
from rawtypes.clang15 import cindex


LOGGER = logging.getLogger(__name__)

SO_UBUNTU = pathlib.Path("/usr/lib/x86_64-linux-gnu/libclang-13.so")
SO_GENTOO = pathlib.Path("/usr/lib/llvm/13/lib64/libclang.so.13")

CINDEX_HEADER: pathlib.Path = pathlib.Path(
    "C:/Program Files/LLVM/include/clang-c/Index.h"
)
if not CINDEX_HEADER.exists():
    raise FileExistsError(CINDEX_HEADER)

CINDEX_VERSION_MINOR_PATTERN = re.compile(r"#define CINDEX_VERSION_MINOR (\d+)")
m = CINDEX_VERSION_MINOR_PATTERN.search(CINDEX_HEADER.read_text())
if not m:
    raise RuntimeError()
minor_version = m.group(1)

CINDEX_VERSION_MINOR_TO_LLVM_VERSION_MAP: dict[str, str] = {
    # https://github.com/llvm/llvm-project/blob/llvmorg-17.0.6/clang/include/clang-c/Index.h
    "64": "17",
    # https://github.com/llvm/llvm-project/blob/llvmorg-16.0.6/clang/include/clang-c/Index.h
    "63": "16",
    # https://github.com/llvm/llvm-project/blob/llvmorg-15.0.7/clang/include/clang-c/Index.h
    "62": "15",
}
LLVM_VERSION = CINDEX_VERSION_MINOR_TO_LLVM_VERSION_MAP.get(minor_version)


class Unsaved(NamedTuple):
    name: str
    content: str


def get_tu(
    entrypoint: str,
    *,
    include_dirs: list[str] | None = None,
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
        arguments.extend(f"-I{i}" for i in include_dirs)
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
    LOGGER.debug(arguments)
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
