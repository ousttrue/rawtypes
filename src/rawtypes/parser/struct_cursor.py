from typing import NamedTuple, Tuple, Dict, Union, List, Optional
import io
import pathlib
#
from rawtypes.clang import cindex
from rawtypes.parser import function_cursor
from rawtypes.parser.function_cursor import FunctionCursor
#
from .type_context import FieldContext


class WrapFlags(NamedTuple):
    name: str
    fields: bool = False
    custom_fields: Dict[str, str] = {}
    methods: Union[bool, Tuple[str, ...]] = False
    custom_methods: Tuple[str, ...] = ()
    default_constructor: bool = False


def is_forward_declaration(cursor: cindex.Cursor) -> bool:
    '''
    https://joshpeterson.github.io/identifying-a-forward-declaration-with-libclang
    '''
    definition = cursor.get_definition()

    # If the definition is null, then there is no definition in this translation
    # unit, so this cursor must be a forward declaration.
    if not definition:
        return True

    # If there is a definition, then the forward declaration and the definition
    # are in the same translation unit. This cursor is the forward declaration if
    # it is _not_ the definition.
    return cursor != definition


class StructCursor(NamedTuple):
    cursors: Tuple[cindex.Cursor, ...]
    record: cindex.Type
    is_union: bool

    def __repr__(self) -> str:
        return f'struct {self.spelling}'

    @property
    def cursor(self) -> cindex.Cursor:
        return self.cursors[-1]

    @property
    def spelling(self) -> str:
        return self.cursor.spelling

    @property
    def name(self) -> str:
        name = self.cursor.spelling
        if name:
            return name
        return f'_{self.cursor.hash}'

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.cursor.location.file.name)

    @property
    def is_forward_decl(self) -> bool:
        definition = self.cursor.get_definition()
        if definition and definition != self.cursor:
            return True
        return False

    @property
    def fields(self) -> List[FieldContext]:
        return FieldContext.get_struct_fields(self.cursor)

    @property
    def sizeof(self) -> int:
        return self.record.get_size()

    def get_methods(self, flags: Optional[WrapFlags] = None) -> List[FunctionCursor]:
        methods = FieldContext.get_struct_methods(
            self.cursor, includes=flags.methods if isinstance(flags, WrapFlags) else True)
        if not methods:
            return []
        return [FunctionCursor(self.cursors + (method,)) for method in methods]

    def get_method(self, name: str) -> FunctionCursor:
        for method in self.get_methods():
            if method.spelling == name:
                return method
        raise KeyError(name)

    def write_pyi(self, type_map, pyi: io.IOBase, *, flags: WrapFlags = WrapFlags('')):
        cursor = self.cursors[-1]

        definition = cursor.get_definition()
        if definition and definition != cursor:
            # skip forward decl
            return

        pyi.write(f'class {cursor.spelling}(ctypes.Structure):\n')
        fields = FieldContext.get_struct_fields(cursor) if flags.fields else []
        if fields:
            for field in fields:
                name = field.name
                if flags.custom_fields.get(name):
                    name = '_' + name
                pyi.write(type_map.from_cursor(field.type, field.cursor).pyi_field(
                    '    ', field.name))
            pyi.write('\n')

        for k, v in flags.custom_fields.items():
            pyi.write('    @property\n')
            l = next(iter(v.splitlines()))
            pyi.write(f'    {l} ...\n')

        methods = FieldContext.get_struct_methods(
            cursor, includes=flags.methods)
        if methods:
            for method in methods:
                function_cursor.write_pyx_method(
                    type_map, pyi, cursor, method, pyi=True)

        for custom in flags.custom_methods:
            l = next(iter(custom.splitlines()))
            pyi.write(f'    {l} ...\n')

        if not fields and not methods:
            pyi.write('    pass\n\n')
