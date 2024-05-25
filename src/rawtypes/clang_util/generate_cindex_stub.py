from typing import NamedTuple, Callable
import types
import dataclasses
import logging
import argparse
import pathlib
import re
import platform
import os
import io
import inspect


LOGGER = logging.getLogger(__name__)
HERE = pathlib.Path(__file__).absolute().parent
CINDEX_VERSION_MINOR_PATTERN = re.compile(r"#define CINDEX_VERSION_MINOR (\d+)")
CINDEX_VERSION_MINOR_TO_LLVM_VERSION_MAP: dict[str, str] = {
    # https://github.com/llvm/llvm-project/blob/llvmorg-17.0.6/clang/include/clang-c/Index.h
    "64": "17",
    # https://github.com/llvm/llvm-project/blob/llvmorg-16.0.6/clang/include/clang-c/Index.h
    "63": "16",
    # https://github.com/llvm/llvm-project/blob/llvmorg-15.0.7/clang/include/clang-c/Index.h
    "62": "15",
}

SO_UBUNTU = pathlib.Path("/usr/lib/x86_64-linux-gnu/libclang-13.so")
SO_GENTOO = pathlib.Path("/usr/lib/llvm/13/lib64/libclang.so.13")


class Unsaved(NamedTuple):
    name: str
    content: str


HARDCODING_TYPE_MAP: dict[str, str] = {
    "kind": "CursorKind",
    "location": "SourceLocation",
    # "spelling": "ctypes.c_char_p",
    "spelling": "str",
}


def generate(src: pathlib.Path, dst_dir: pathlib.Path) -> None:
    if not src.exists():
        raise FileExistsError(src)
    m = CINDEX_VERSION_MINOR_PATTERN.search(src.read_text())
    if not m:
        raise RuntimeError()
    minor_version = m.group(1)
    llvm_version = CINDEX_VERSION_MINOR_TO_LLVM_VERSION_MAP.get(minor_version)
    match llvm_version:
        case "15":
            from rawtypes.clang15 import cindex
        # case "16":
        #     from ..clang16 import cindex
        # case "17":
        #     from ..clang17 import cindex
        case _:
            raise NotImplementedError(minor_version)

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

    def _traverse(
        callback: Callable[[cindex.Cursor], bool], *cursor_path: cindex.Cursor
    ):
        if callback(*cursor_path):
            for child in cursor_path[-1].get_children():
                _traverse(callback, *cursor_path, child)

    def traverse(tu: cindex.TranslationUnit, callback: Callable[[cindex.Cursor], bool]):
        for child in tu.cursor.get_children():
            _traverse(callback, child)

    def remove_prefix(values: list[str]) -> list[str]:
        def get_prefix(l: str, r: str):
            i = 0
            for i in range(len(l)):
                if l[i] != r[i]:
                    break
            return l[:i]

        prefix = get_prefix(values[0], values[1])
        for value in values[2:]:
            if not value.startswith(prefix):
                prefix = get_prefix(value, prefix)

        # LOGGER.debug(f"prefix: {prefix}")

        return [value[len(prefix) :] for value in values]

    def upper_snake(s: str) -> str:
        return "_".join(
            re.sub(
                r"(\s|_|-)+",
                " ",
                re.sub(
                    r"[A-Z]{2,}(?=[A-Z][a-z]+[0-9]*|\b)|[A-Z]?[a-z]+[0-9]*|[A-Z]|[0-9]+",
                    lambda mo: " " + mo.group(0).upper(),
                    s,
                ),
            ).split()
        )

    class TranslationUnitFlags(NamedTuple):
        children: list[str]

    def generate_enum(
        w: io.IOBase,
        tu: cindex.TranslationUnit,
        functions: list[tuple[cindex.Cursor, ...]],
    ) -> TranslationUnitFlags:
        used: set[str] = set()
        flags = TranslationUnitFlags([])

        for f in functions:
            c = f[-1]
            if c.spelling:
                if c.spelling in used:
                    continue

                children: list[str] = []
                for child in c.get_children():
                    if child.kind == cindex.CursorKind.ENUM_CONSTANT_DECL:
                        children.append(child.spelling)

                if len(children) > 1:
                    # LOGGER.debug(c.spelling)
                    used.add(c.spelling)

                    children = remove_prefix(children)
                    children = [upper_snake(child) for child in children]

                    name = c.spelling[2:]  # remove prefix CX

                    if name == "TypeKind":
                        children = [child.replace("_", "") for child in children]
                    if name == "TranslationUnit_Flags":
                        flags.children.extend(children)
                    else:
                        w.write(f"class {name}(BaseEnumeration):\n")
                        for child in children:
                            w.write(f"    {child}: ClassVar[{name}]\n")
                    w.write("\n")

        return flags

    def generate_instance(
        w: io.IOBase, obj: object, flags: TranslationUnitFlags | None = None
    ):
        LOGGER.debug(obj.__class__.__name__)
        w.write(f"class {obj.__class__.__name__}:\n")

        if obj.__class__.__name__ == "TranslationUnit" and flags:
            # name = "TranslationUnit"
            # w.write(f"class {name}(BaseEnumeration):\n")
            for child in flags.children:
                if child == "DETAILED_PREPROCESSING_RECORD":
                    # typo ?
                    child = "DETAILED_PROCESSING_RECORD"
                w.write(f"    PARSE_{child}: ClassVar[int]\n")

        for k, v in obj.__class__.__dict__.items():
            # print(k, v)
            if isinstance(v, types.FunctionType):
                args = inspect.signature(v)
                ret = ""
                if k == "get_children":
                    ret = "->Iterator[Cursor]"
                elif k in ("__eq__", "__ne__"):
                    ret = "->bool"
                elif k.startswith("is_"):
                    ret = "->bool"
                w.write(f"    def {k}{args}{ret}:")
                if v.__doc__:
                    w.write('\n        """')
                    w.write(v.__doc__)
                    w.write('"""\n')
                    w.write("        ...\n")
                else:
                    w.write(" ...\n")
            elif isinstance(v, property):
                found = HARDCODING_TYPE_MAP.get(k, "Any")
                w.write(f"    @property\n")
                w.write(f"    def {k}(self)->{found}:...\n")
        w.write("\n")

    @dataclasses.dataclass
    class Parser:
        entrypoint: str
        tu: cindex.TranslationUnit
        functions: list[tuple[cindex.Cursor, ...]] = dataclasses.field(
            default_factory=list
        )
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

    parser = Parser.create(str(src))
    parser.traverse()

    dst = dst_dir / f"rawtypes/clang{llvm_version}/cindex/__init__.pyi"
    dst.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.info(f"{src} => {dst}")
    with dst.open("w") as w:
        w.write(
            """from typing import ClassVar, Any, Iterator


class BaseEnumeration(object):
    pass

"""
        )
        flags = generate_enum(w, parser.tu, parser.enums)

        # from object instance
        generate_instance(w, parser.tu, flags)

        # cursor
        generate_instance(w, parser.enums[0][0])
        # location
        generate_instance(w, parser.enums[0][0].location)
        # type
        generate_instance(w, parser.functions[0][-1].result_type)


def main():
    logging.basicConfig(
        format="[%(levelname)s] %(filename)s:%(lineno)d => %(message)s",
        level=logging.DEBUG,
    )
    parser = argparse.ArgumentParser(
        prog="cindex stub generator",
        description="pyi from LLVM/include/clang-c/Index.h",
    )
    parser.add_argument(
        "--src",
        help="path to clang-c/Index.h",
        type=pathlib.Path,
        default="C:/Program Files/LLVM/include/clang-c/Index.h",
    )
    # ubuntu: libclang-13-dev
    # "/usr/lib/llvm-13/include/clang-c/Index.h"

    parser.add_argument(
        "dst",
        help="root directory for pyi. DST_DIR/rawtypes/clangXX/cindex.pyi will be generated.",
        type=pathlib.Path,
        default=HERE / "typings",
    )
    args = parser.parse_args()

    generate(args.src, args.dst)


if __name__ == "__main__":
    main()
