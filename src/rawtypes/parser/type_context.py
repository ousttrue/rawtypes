from typing import NamedTuple, Optional, List
import logging
import re
from rawtypes.clang import cindex

logger = logging.getLogger(__name__)

TEMPLATE_PATTERN = re.compile(r'<[^>]+>')


def symbol_filter(src: str) -> str:
    '''
    fix python reserved word
    '''
    match src:
        case 'in' | 'id':
            return '_' + src
        case _:
            return src


class TypeContext(NamedTuple):
    '''
    function result_type(index = -1)
    function param type
    struct field type
    '''
    index: int
    type: cindex.Type
    cursor: cindex.Cursor

    # def remove_namespce(self, src: str) -> str:
    #     return src.replace(self.namespace, '')

    @staticmethod
    def from_function_result(cursor: cindex.Cursor):
        return TypeContext(-1, cursor.result_type, cursor)

    @staticmethod
    def from_function_param(index: int, cursor: cindex.Cursor):
        return TypeContext(index, cursor.type, cursor)

    @staticmethod
    def get_function_params(cursor: cindex.Cursor):
        cursors = [child for child in cursor.get_children(
        ) if child.kind == cindex.CursorKind.PARM_DECL]
        return [TypeContext.from_function_param(i, child) for i, child in enumerate(cursors)]

    @staticmethod
    def from_struct_field(index: int, cursor: cindex.Cursor):
        return TypeContext(index, cursor.type, cursor)

    @staticmethod
    def get_struct_fields(cursor: cindex.Cursor) -> List['TypeContext']:
        cursors = []
        for child in cursor.get_children():
            if not isinstance(child, cindex.Cursor):
                raise RuntimeError()
            match child.kind:
                case cindex.CursorKind.FIELD_DECL:
                    cursors.append(child)
                case cindex.CursorKind.UNION_DECL:
                    if child.type.kind == cindex.TypeKind.RECORD:
                        cursors.append(child)
                    else:
                        # innner type decl ?
                        pass
                case cindex.CursorKind.STRUCT_DECL:
                    if child.type.kind == cindex.TypeKind.RECORD:
                        cursors.append(child)
                    else:
                        # inner type decl ?
                        pass
                case _:
                    pass
        return [TypeContext.from_struct_field(i, child) for i, child in enumerate(cursors)]

    @staticmethod
    def get_struct_methods(cursor: cindex.Cursor, *, excludes=(), includes=False) -> List[cindex.Cursor]:
        def method_filter(method: cindex.Cursor) -> bool:
            if method.kind != cindex.CursorKind.CXX_METHOD:
                return False
            for param in method.get_children():
                if param.kind == cindex.CursorKind.PARM_DECL and param.type.spelling in excludes:
                    return False
            match includes:
                case True:
                    # return True
                    pass
                case False:
                    return False
                case (*methods,):
                    if method.spelling not in methods:
                        return False
                    else:
                        pass
            if method.result_type.spelling in excludes:
                return False
            return True
        return [child for child in cursor.get_children() if method_filter(child)]

    @staticmethod
    def get_constructors(cursor: cindex.Cursor) -> List[cindex.Cursor]:
        return [child for child in cursor.get_children() if child.kind == cindex.CursorKind.CONSTRUCTOR]

    @staticmethod
    def get_default_constructor(cursor: cindex.Cursor) -> Optional[cindex.Cursor]:
        for constructor in TypeContext.get_constructors(cursor):
            params = TypeContext.get_function_params(constructor)
            if len(params) == 0:
                return constructor

    @property
    def name(self) -> str:
        name = self.cursor.spelling
        if not name:
            # anonymous
            return f'_{self.cursor.hash}'
        return symbol_filter(name)

    @property
    def is_void(self) -> bool:
        return self.type.kind == cindex.TypeKind.VOID

    @property
    def is_const(self) -> bool:
        if self.type.is_const_qualified():
            return True
        match self.type.kind:
            case cindex.TypeKind.POINTER | cindex.TypeKind.LVALUEREFERENCE:
                if self.type.get_pointee().is_const_qualified():
                    return True
        return False

    @property
    def is_anonymous_field(self) -> bool:
        return self.cursor.is_anonymous()

    def default_value(self, use_filter: bool) -> str:
        tokens = []
        for child in self.cursor.get_children():
            # logger.debug(child.spelling)
            match child.kind:
                case cindex.CursorKind.UNEXPOSED_EXPR | cindex.CursorKind.INTEGER_LITERAL | cindex.CursorKind.FLOATING_LITERAL | cindex.CursorKind.CXX_BOOL_LITERAL_EXPR | cindex.CursorKind.UNARY_OPERATOR | cindex.CursorKind.CALL_EXPR:
                    tokens = [
                        token.spelling for token in self.cursor.get_tokens()]
                    if '=' not in tokens:
                        tokens = []
                case cindex.CursorKind.TYPE_REF | cindex.CursorKind.TEMPLATE_REF | cindex.CursorKind.NAMESPACE_REF:
                    pass
                case _:
                    logger.debug(f'{self.cursor.spelling}: {child.kind}')

        if not tokens:
            return ''

        def token_filter(src: str) -> str:

            match src:
                case 'NULL' | 'nullptr':
                    return 'None'
                case 'true':
                    return 'True'
                case 'false':
                    return 'False'
                case 'FLT_MAX':
                    return '3.402823466e+38'
                case 'FLT_MIN':
                    return '1.175494351e-38'
                case _:
                    if src.startswith('"'):
                        # string literal
                        return 'b' + src
                    if re.search(r'[\d.]f$', src):
                        return src[:-1]

                    return src

        equal = tokens.index('=')

        if use_filter:
            value = ' '.join(token_filter(t) for t in tokens[equal+1:])
        else:
            value = ' '.join(t for t in tokens[equal+1:])

        return '= ' + value
