from typing import NamedTuple, Tuple
import io
from rawtypes.clang import cindex
import pathlib


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
        for child in self.cursor.get_children():
            if child.kind == cindex.CursorKind.ENUM_CONSTANT_DECL:
                name = child.spelling
                if name.startswith(self.cursor.spelling):
                    name = name[len(self.cursor.spelling):]
                if name == 'None':
                    name = 'NONE'
                w.write(f'    {name} = {hex(child.enum_value)}\n')
        w.write('\n')
