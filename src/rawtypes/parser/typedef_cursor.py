from typing import NamedTuple, Tuple
import pathlib
import re
from rawtypes.clang import cindex


FP_PATTERN = re.compile(r'(.*)\(\*\)(.*)')


def type_name(t: str, name: str) -> str:
    m = FP_PATTERN.match(t)
    if m:
        # function pointer
        return f'{m.group(1)}(*{name}){m.group(2)}'
    else:
        return f'{t} {name}'


class TypedefCursor(NamedTuple):
    cursors: Tuple[cindex.Cursor, ...]

    def __repr__(self) -> str:
        return f'{self.spelling} = {self.underlying_type.spelling}'

    @property
    def cursor(self) -> cindex.Cursor:
        return self.cursors[-1]

    @property
    def spelling(self) -> str:
        return self.cursor.spelling

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.cursor.location.file.name)

    @property
    def underlying_type(self) -> cindex.Type:
        return self.cursor.underlying_typedef_type

    def has_underlying(self, cursor: cindex.Cursor) -> bool:
        for child in self.cursor.get_children():
            if child == cursor:
                return True
            match child.kind:
                case cindex.CursorKind.TYPE_REF:
                    if child.referenced == cursor:
                        return True
                case cindex.CursorKind.STRUCT_DECL | cindex.CursorKind.UNION_DECL:
                    pass
                case cindex.CursorKind.PARM_DECL:
                    pass
                case cindex.CursorKind.ENUM_DECL:
                    pass
                case _:
                    raise NotImplementedError()
        return False
