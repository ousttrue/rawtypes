from typing import NamedTuple, Tuple, Iterable
import io
from rawtypes.clang import cindex
import pathlib


def escape(name: str):
    if name[0] in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
        return '_' + name
    if name == '_PendingRemoval_':
        return name + '_'
    return name


class EnumCursor(NamedTuple):
    cursors: Tuple[cindex.Cursor, ...]

    @property
    def cursor(self) -> cindex.Cursor:
        return self.cursors[-1]

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.cursor.location.file.name)

    def write_to(self, w: io.IOBase):
        w.write(f'class {self.cursor.spelling}(IntEnum):\n')
        for child in self.get_values():
            name = child.spelling
            if name.startswith(self.cursor.spelling):
                name = name[len(self.cursor.spelling):]
            if name == 'None':
                name = 'NONE'
            w.write(f'    {escape(name)} = {hex(child.enum_value)}\n')
        w.write('\n')

    def get_values(self) -> Iterable[cindex.Cursor]:
        for child in self.cursor.get_children():
            if child.kind == cindex.CursorKind.ENUM_CONSTANT_DECL:
                yield child
