from typing import NamedTuple, Tuple, Dict, Union, List, Optional
import io
import pathlib
#
from rawtypes.clang import cindex
from rawtypes.parser import function_cursor
from rawtypes.parser.function_cursor import FunctionCursor
#
from .typewrap import TypeWrap


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
    def is_forward_decl(self) -> bool:
        definition = self.cursor.get_definition()
        if definition and definition != self.cursor:
            return True
        return False

    def get_methods(self, flags: Optional[WrapFlags] = None) -> List[FunctionCursor]:
        methods = TypeWrap.get_struct_methods(
            self.cursor, includes=flags.methods if isinstance(flags, WrapFlags) else True)
        if not methods:
            return []
        return [FunctionCursor(self.cursors + (method,)) for method in methods]

    def get_method(self, name: str) -> FunctionCursor:
        for method in self.get_methods():
            if method.spelling == name:
                return method
        raise KeyError(name)

    def write_pxd(self, pxd: io.IOBase, *, excludes=()):
        cursor = self.cursors[-1]

        constructors = [child for child in cursor.get_children(
        ) if child.kind == cindex.CursorKind.CONSTRUCTOR]

        methods = TypeWrap.get_struct_methods(
            cursor, excludes=excludes, includes=True)
        if cursor.kind == cindex.CursorKind.CLASS_TEMPLATE:
            pxd.write(f'    cppclass {cursor.spelling}[T]')
        elif constructors or methods:
            pxd.write(f'    cppclass {cursor.spelling}')
        else:
            definition = cursor.get_definition()
            if definition and any(child for child in definition.get_children() if child.kind == cindex.CursorKind.CONSTRUCTOR):
                # forward decl
                pxd.write(f'    cppclass {cursor.spelling}')
            else:
                pxd.write(f'    struct {cursor.spelling}')

        fields = TypeWrap.get_struct_fields(cursor)
        if constructors or fields:
            pxd.write(':\n')

            for field in fields:
                pxd.write(f'        {field.c_type_with_name}\n')

            for child in constructors:
                function_cursor.write_pxd_constructor(pxd, cursor, child)

            for child in methods:
                function_cursor.write_pxd_method(pxd, child)

        pxd.write('\n')

    def write_pyx_ctypes(self, generator, pyx: io.IOBase, *, flags: WrapFlags = WrapFlags('')):
        cursor = self.cursors[-1]

        definition = cursor.get_definition()
        if definition and definition != cursor:
            # skip forward decl
            return

        pyx.write(f'class {cursor.spelling}(ctypes.Structure):\n')
        fields = TypeWrap.get_struct_fields(cursor) if flags.fields else []
        if fields:
            pyx.write('    _fields_=[\n')
            indent = '        '
            for field in fields:
                name = field.name
                if flags.custom_fields.get(name):
                    name = '_' + name
                pyx.write(generator.from_cursor(field.cursor.type,
                          field.cursor).ctypes_field(indent, name))
            pyx.write('    ]\n\n')

        if flags.default_constructor:
            constructor = TypeWrap.get_default_constructor(cursor)
            if constructor:
                pyx.write(f'''    def __init__(self, **kwargs):
        p = new impl.{cursor.spelling}()
        memcpy(<void *><uintptr_t>ctypes.addressof(self), p, sizeof(impl.{cursor.spelling}))
        del p
        super().__init__(**kwargs)

''')

        for _, v in flags.custom_fields.items():
            pyx.write('    @property\n')
            for l in v.splitlines():
                pyx.write(f'    {l}\n')
            pyx.write('\n')

        methods = TypeWrap.get_struct_methods(cursor, includes=flags.methods)
        if methods:
            for method in methods:
                function_cursor.write_pyx_method(
                    generator, pyx, cursor, method)

        for code in flags.custom_methods:
            for l in code.splitlines():
                pyx.write(f'    {l}\n')
            pyx.write('\n')

        if not fields and not methods and not flags.custom_methods:
            pyx.write('    pass\n\n')

    def write_pyi(self, type_map, pyi: io.IOBase, *, flags: WrapFlags = WrapFlags('')):
        cursor = self.cursors[-1]

        definition = cursor.get_definition()
        if definition and definition != cursor:
            # skip forward decl
            return

        pyi.write(f'class {cursor.spelling}(ctypes.Structure):\n')
        fields = TypeWrap.get_struct_fields(cursor) if flags.fields else []
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

        methods = TypeWrap.get_struct_methods(cursor, includes=flags.methods)
        if methods:
            for method in methods:
                function_cursor.write_pyx_method(
                    type_map, pyi, cursor, method, pyi=True)

        for custom in flags.custom_methods:
            l = next(iter(custom.splitlines()))
            pyi.write(f'    {l} ...\n')

        if not fields and not methods:
            pyi.write('    pass\n\n')