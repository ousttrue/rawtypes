from typing import NamedTuple, Tuple, Dict, Union, List, Optional, Iterable
import io
import pathlib
#
from rawtypes.clang import cindex
from rawtypes.parser import function_cursor
from rawtypes.parser.function_cursor import FunctionCursor
#
from .type_context import FieldContext


class WrapFlags(NamedTuple):
    submodule: str
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


def get_struct_children(in_union: bool, cursors: Tuple[cindex.Cursor, ...]) -> Iterable[Union['FieldContext', 'StructCursor']]:
    field_index = 0
    for child in cursors[-1].get_children():
        if not isinstance(child, cindex.Cursor):
            raise RuntimeError()
        match child.kind:
            case cindex.CursorKind.FIELD_DECL:
                yield FieldContext(field_index, child, child.type)
                field_index += 1
            case cindex.CursorKind.UNION_DECL:
                yield StructCursor(cursors+(child,), child.type, True)
            case cindex.CursorKind.STRUCT_DECL:
                yield StructCursor(
                    cursors+(child,), child.type, False)
            case _:
                pass


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
        if self.cursor.spelling:
            return self.cursor.spelling

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
    def is_template(self) -> bool:
        display_name = self.cursor.displayname
        return display_name and (display_name[-1] == '>')

    @property
    def decls(self) -> List['StructCursor']:
        return [child for child in get_struct_children(self.is_union, self.cursors) if isinstance(child, StructCursor)]

    @property
    def fields(self) -> List[FieldContext]:
        return [child for child in get_struct_children(
            self.is_union, self.cursors) if isinstance(child, FieldContext)]

    @property
    def sizeof(self) -> int:
        return self.record.get_size()

    def get_methods(self, flags: Optional[WrapFlags] = None) -> List[FunctionCursor]:
        methods = FieldContext.get_struct_methods(
            self.cursor, includes=flags.methods if isinstance(flags, WrapFlags) else True)
        if not methods:
            return []
        return [FunctionCursor(method.result_type, self.cursors + (method,)) for method in methods]

    def get_method(self, name: str) -> FunctionCursor:
        for method in self.get_methods():
            if method.spelling == name:
                return method
        raise KeyError(name)
