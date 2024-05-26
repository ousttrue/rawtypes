from typing import NamedTuple
import re
import inspect
import types
import logging
import io
import argparse
import pathlib
from .. import cindex_util
from ..clang15 import cindex

LOGGER = logging.getLogger(__name__)


HARDCODING_TYPE_MAP: dict[str, str] = {
    "kind": "CursorKind",
    "location": "SourceLocation",
    # "spelling": "ctypes.c_char_p",
    "spelling": "str",
    "hash": "int",
}

HARDCODING_METHOD_MAP: dict[str, str] = {
    "get_children": "->list[Cursor]",
    "get_tokens": "->Iterator[Token]",
    "__eq__": "->bool",
    "__ne__": "->bool",
}


class TranslationUnitFlags(NamedTuple):
    children: list[str]


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
) -> None:
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
            if k in HARDCODING_METHOD_MAP:
                ret = HARDCODING_METHOD_MAP[k]
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


def generate(src: pathlib.Path, dst_dir: pathlib.Path) -> None:

    parser = cindex_util.Parser.create(str(src))
    parser.traverse()

    dst = dst_dir / f"rawtypes/clang{cindex_util.LLVM_VERSION}/cindex.pyi"
    dst.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.info(f"{src} => {dst}")
    with dst.open("w") as w:
        w.write(
            """from typing import ClassVar, Any, Iterator
import ctypes

        
class Token(ctypes.Structure):
    _fields_ = [
        ('int_data', c_uint * 4),
        ('ptr_data', c_void_p)
    ]
    @property
    def spelling(self)->str:...
    @property
    def kind(self):...
    @property
    def location(self):...
    @property
    def extent(self):...
    @property
    def cursor(self):...

    
class BaseEnumeration(object):
    pass

"""
        )
        flags = generate_enum(w, parser.tu, parser.enums)
        # from object instance
        generate_instance(w, parser.tu, flags)
        # cursor
        generate_instance(w, parser.enums[0][0], None)
        # location
        generate_instance(w, parser.enums[0][0].location, None)
        # type
        generate_instance(w, parser.functions[0][-1].result_type, None)


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
        help="root directory for pyi. DST_DIR/rawtypes/clang15/cindex.pyi will be generated.",
        type=pathlib.Path,
    )
    args = parser.parse_args()

    generate(args.src, args.dst)


if __name__ == "__main__":
    main()
