from typing import List, Tuple
import types
import logging
import argparse
import pathlib
import io
import pathlib
import re
from inspect import signature
from rawtypes import clang_util
from rawtypes.clang import cindex

HERE = pathlib.Path(__file__).absolute().parent
logger = logging.getLogger(__name__)


class Parser:
    def __init__(self, entrypoint: str):
        self.entrypoint = entrypoint
        self.tu = clang_util.get_tu(self.entrypoint)
        self.functions = []
        self.enums = []

    def filter(self, *cursor_path: cindex.Cursor):
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
        clang_util.traverse(self.tu, self.filter)


def remove_prefix(values: List[str]):
    def get_prefix(l, r):
        i = 0
        for i in range(len(l)):
            if l[i] != r[i]:
                break
        return l[:i]

    prefix = get_prefix(values[0], values[1])
    for value in values[2:]:
        if not value.startswith(prefix):
            prefix = get_prefix(value, prefix)

    logger.debug(f'prefix: {prefix}')

    return [value[len(prefix):] for value in values]


def upper_snake(s: str):
    return '_'.join(
        re.sub(r"(\s|_|-)+", " ",
               re.sub(r"[A-Z]{2,}(?=[A-Z][a-z]+[0-9]*|\b)|[A-Z]?[a-z]+[0-9]*|[A-Z]|[0-9]+",
                      lambda mo: ' ' + mo.group(0).upper(), s)).split())


def generate_enum(w: io.IOBase, tu, functions: List[Tuple[cindex.Cursor, ...]]):
    used = set()
    for f in functions:
        c = f[-1]
        if c.spelling:
            if c.spelling in used:
                continue

            children = []
            for child in c.get_children():
                if child.kind == cindex.CursorKind.ENUM_CONSTANT_DECL:
                    children.append(child.spelling)

            if len(children) > 1:
                logger.debug(c.spelling)
                used.add(c.spelling)

                children = remove_prefix(children)
                children = [upper_snake(child) for child in children]

                name = c.spelling[2:]  # remove prefix CX
                if name == 'TypeKind':
                    children = [child.replace('_', '') for child in children]
                if name == 'TranslationUnit_Flags':
                    name = 'TranslationUnit'
                    w.write(f'class {name}(BaseEnumeration):\n')
                    for child in children:
                        w.write(f'    PARSE_{child}: ClassVar[{name}]\n')
                else:
                    w.write(f'class {name}(BaseEnumeration):\n')
                    for child in children:
                        w.write(f'    {child}: ClassVar[{name}]\n')
                w.write('\n')


def generate_instance(w: io.IOBase, obj: object):
    logger.debug(obj.__class__.__name__)
    w.write(f'class {obj.__class__.__name__}:\n')
    for k, v in obj.__class__.__dict__.items():
        # print(k, v)
        if isinstance(v, types.FunctionType):
            args = signature(v)
            w.write(f'    def {k}{args}:')
            if v.__doc__:
                w.write('\n        """')
                w.write(v.__doc__)
                w.write('"""\n')
                w.write('        ...\n')
            else:
                w.write(' ...\n')
        elif isinstance(v, property):
            w.write(f'    {k}: Any\n')
    w.write('\n')


def generate(src: pathlib.Path, dst: pathlib.Path):
    parser = Parser(str(src))
    parser.traverse()
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open('w') as w:
        w.write('''from typing import ClassVar, Any

class BaseEnumeration(object):
    pass

''')
        generate_enum(w, parser.tu, parser.enums)

        # from object instance
        # generate_instance(w, parser.tu)

        # cursor
        generate_instance(w, parser.enums[0][0])
        # location
        generate_instance(w, parser.enums[0][0].location)
        # type
        generate_instance(w, parser.functions[0][-1].result_type)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument('--src')
    parser.add_argument('--dst')
    args = parser.parse_args()

    src = pathlib.Path(
        args.src if args.src else "C:/Program Files/LLVM/include/clang-c/Index.h").absolute()

    dst = pathlib.Path(
        args.dst if args.dst else (HERE.parent.parent.parent / "src/rawtypes/clang/cindex.pyi")).absolute()

    generate(src, dst)
