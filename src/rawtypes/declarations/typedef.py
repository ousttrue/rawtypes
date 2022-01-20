from typing import NamedTuple, Tuple
import io
import re
from rawtypes.clang import cindex
from ..interpreted_types.wrap_types import WrapFlags

FP_PATTERN = re.compile(r'(.*)\(\*\)(.*)')


def type_name(t: str, name: str) -> str:
    m = FP_PATTERN.match(t)
    if m:
        # function pointer
        return f'{m.group(1)}(*{name}){m.group(2)}'
    else:
        return f'{t} {name}'


class TypedefDecl(NamedTuple):
    cursors: Tuple[cindex.Cursor, ...]

    @property
    def cursor(self) -> cindex.Cursor:
        return self.cursors[-1]

    def write_pxd(self, pxd: io.IOBase, *, excludes=()):
        cursor = self.cursors[-1]
        underlying_type = cursor.underlying_typedef_type
        pxd.write(
            f'    ctypedef {type_name(underlying_type.spelling, cursor.spelling)}\n')

    def write_pyx_ctypes(self, pyx: io.IOBase, *, flags: WrapFlags = WrapFlags('')):
        pass

    def write_pyi(self, pyi: io.IOBase, *, flags: WrapFlags = WrapFlags('')):
        pass
