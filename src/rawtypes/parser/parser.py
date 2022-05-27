from typing import List, Union, Iterable
import io
import pathlib
import logging
from rawtypes.clang import cindex
from rawtypes import clang_util
from .typedef_cursor import TypedefCursor
from .struct_cursor import StructCursor
from .enum_cursor import EnumCursor
from .function_cursor import FunctionCursor
logger = logging.getLogger(__name__)


class Parser:
    def __init__(self, tu: cindex.TranslationUnit, headers: List[pathlib.Path]) -> None:
        self.tu = tu
        self.headers = headers
        self.functions: List[FunctionCursor] = []
        self.enums: List[EnumCursor] = []
        self.typedef_struct_list: List[Union[TypedefCursor, StructCursor]] = []
        self.used = []
        self.skip = []

    @staticmethod
    def parse(headers: Iterable[pathlib.Path], *, include_dirs: Iterable[pathlib.Path] = (), definitions=(), target='') -> "Parser":
        headers = list(headers)

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
                logger.debug(f'header: {location.file.name}')
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
                        self.functions.append(FunctionCursor(cursor_path[-1].result_type, cursor_path))
                case cindex.CursorKind.ENUM_DECL:
                    self.enums.append(EnumCursor(cursor_path))
                case cindex.CursorKind.TYPEDEF_DECL:
                    self.typedef_struct_list.append(TypedefCursor(cursor_path))
                case cindex.CursorKind.STRUCT_DECL:
                    self.typedef_struct_list.append(
                        StructCursor(cursor_path, cursor.type, False))
                case cindex.CursorKind.CLASS_TEMPLATE:
                    self.typedef_struct_list.append(
                        StructCursor(cursor_path, cursor.type, False))
                case cindex.CursorKind.CLASS_DECL:
                    self.typedef_struct_list.append(
                        StructCursor(cursor_path, cursor.type, False))
                case cindex.CursorKind.UNEXPOSED_DECL:
                    # extern C etc...
                    return True
                case cindex.CursorKind.VAR_DECL:
                    pass
                case _:
                    logger.debug(cursor.kind)

        else:
            if location.file.name.startswith('C:') or location.file.name.startswith('/usr'):
                pass
            else:
                if location.file.name not in self.skip:
                    if location.file.name != 'tmp.h':
                        logger.debug(f'unknown header: {location.file.name}')
                    self.skip.append(location.file.name)

        return False

    def _traverse(self):
        clang_util.traverse(self.tu, self._callback)

    def get_function(self, name: str) -> FunctionCursor:
        for f in self.functions:
            if f.spelling == name:
                return f
        raise KeyError(name)

    def get_struct(self, name: str) -> StructCursor:
        found = None
        for s in self.typedef_struct_list:
            if isinstance(s, StructCursor):
                if s.cursor.spelling == name or s.cursor.spelling == 'struct ' + name:
                    if not s.is_forward_decl:
                        return s
                    found = s
                    print(s)
        if found:
            return found
        raise KeyError(name)
