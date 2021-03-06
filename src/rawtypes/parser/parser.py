from typing import List, Union, Iterable, TypeAlias, Optional
import io
import pathlib
import logging
from rawtypes.clang import cindex
from rawtypes import clang_util
from .typedef_cursor import TypedefCursor
from .struct_cursor import StructCursor
from .enum_cursor import EnumCursor
from .function_cursor import FunctionCursor
LOGGER = logging.getLogger(__name__)

DeclCursor: TypeAlias = Union[FunctionCursor,
                              EnumCursor, TypedefCursor, StructCursor]


class Parser:
    def __init__(self, tu: cindex.TranslationUnit, headers: List[pathlib.Path]) -> None:
        self.tu = tu
        self.headers = headers
        self.decls: List[DeclCursor] = []
        self.used = []
        self.skip = []

    @staticmethod
    def parse(headers: Iterable[pathlib.Path], *, include_dirs: Iterable[pathlib.Path] = (), definitions=(), target='') -> "Parser":
        headers = list(headers)
        for header in headers:
            assert(header.exists())

        sio = io.StringIO()
        for header in headers:
            sio.write(f'#include "{header.name}"\n')

        _include_dirs = [str(header.parent)
                         for header in headers] + [str(dir) for dir in include_dirs]
        unsaved = clang_util.Unsaved('tmp.h', sio.getvalue())
        tu = clang_util.get_tu(
            'tmp.h', include_dirs=_include_dirs, definitions=definitions, unsaved=[unsaved], flags=[], target=target)

        parser = Parser(tu, headers)
        parser._traverse()
        return parser

    @staticmethod
    def parse_source(src: str) -> "Parser":
        tu = clang_util.get_tu(
            'tmp.h', unsaved=[clang_util.Unsaved('tmp.h', src)])
        parser = Parser(tu, [pathlib.Path('tmp.h')])
        parser._traverse()
        return parser

    def _callback(self, *cursor_path: cindex.Cursor) -> bool:
        cursor = cursor_path[-1]
        location: cindex.SourceLocation = cursor.location
        if not location:
            return False
        if not location.file:
            return False

        if pathlib.Path(location.file.name) in self.headers:
            if location.file.name not in self.used:
                LOGGER.debug(f'header: {location.file.name}')
                self.used.append(location.file.name)
            match cursor.kind:
                case cindex.CursorKind.NAMESPACE:
                    # enter namespace
                    # logger.info(f'namespace: {cursor.spelling}')
                    return True
                case (
                    cindex.CursorKind.MACRO_DEFINITION
                    | cindex.CursorKind.INCLUSION_DIRECTIVE
                    | cindex.CursorKind.FUNCTION_TEMPLATE
                ):
                    pass

                case cindex.CursorKind.MACRO_INSTANTIATION:
                    pass

                case (
                    cindex.CursorKind.NAMESPACE_REF
                    | cindex.CursorKind.TEMPLATE_REF
                ):
                    pass

                case cindex.CursorKind.FUNCTION_DECL:
                    if(cursor.spelling.startswith('operator ')):
                        pass
                    else:
                        self.decls.append(FunctionCursor(
                            cursor_path[-1].result_type, cursor_path))
                case cindex.CursorKind.ENUM_DECL:
                    self.decls.append(EnumCursor(cursor_path))
                case cindex.CursorKind.TYPEDEF_DECL:
                    self.decls.append(TypedefCursor(cursor_path))
                case cindex.CursorKind.STRUCT_DECL:
                    self.decls.append(
                        StructCursor(cursor_path, cursor.type, False))
                case cindex.CursorKind.CLASS_TEMPLATE:
                    self.decls.append(
                        StructCursor(cursor_path, cursor.type, False))
                case cindex.CursorKind.CLASS_DECL:
                    self.decls.append(
                        StructCursor(cursor_path, cursor.type, False))
                case cindex.CursorKind.UNEXPOSED_DECL:
                    # extern C etc...
                    return True
                case cindex.CursorKind.VAR_DECL:
                    pass
                case _:
                    LOGGER.debug(cursor.kind)

        else:
            if location.file.name.startswith('C:') or location.file.name.startswith('/usr'):
                pass
            else:
                if location.file.name not in self.skip:
                    if location.file.name != 'tmp.h':
                        LOGGER.debug(f'unknown header: {location.file.name}')
                    self.skip.append(location.file.name)

        return False

    def _traverse(self):
        clang_util.traverse(self.tu, self._callback)

    def get_function(self, name: str) -> FunctionCursor:
        for d in self.decls:
            if isinstance(d, FunctionCursor):
                if d.spelling == name:
                    return d
        raise KeyError(name)

    def get_struct(self, name: str) -> StructCursor:
        found = None
        for d in self.decls:
            if isinstance(d, StructCursor):
                if d.cursor.spelling == name or d.cursor.spelling == 'struct ' + name:
                    if not d.is_forward_decl:
                        return d
                    found = d
                    print(d)
        if found:
            return found
        raise KeyError(name)

    def find_typedef(self, underlying: cindex.Cursor) -> Optional[TypedefCursor]:
        for d in self.decls:
            if isinstance(d, TypedefCursor):
                if d.has_underlying(underlying):
                    return d
