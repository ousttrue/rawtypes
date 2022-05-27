from lib2to3.pgen2 import token
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


class TypeContext:
    type: cindex.Type
    cursor: cindex.Cursor

    def __init__(self, type: cindex.Type, cursor: cindex.Cursor) -> None:
        self.type = type
        self.cursor = cursor

    def __str__(self) -> str:
        return f'{self.cursor.spelling}'

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
            params = ParamContext.get_function_params(constructor)
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


class DefaultValue:
    def __init__(self, tokens: List[str]) -> None:
        self.tokens = tokens

    @staticmethod
    def create(cursor: cindex.Cursor) -> Optional['DefaultValue']:
        tokens = []
        children = []
        for child in cursor.get_children():
            children.append(child)
            match child.kind:
                case (cindex.CursorKind.UNEXPOSED_EXPR
                      | cindex.CursorKind.INTEGER_LITERAL
                      | cindex.CursorKind.FLOATING_LITERAL
                      | cindex.CursorKind.CXX_BOOL_LITERAL_EXPR
                      | cindex.CursorKind.UNARY_OPERATOR
                      | cindex.CursorKind.CALL_EXPR
                      | cindex.CursorKind.PARM_DECL
                      | cindex.CursorKind.CXX_NULL_PTR_LITERAL_EXPR  # bool
                      ):
                    tokens = [
                        token.spelling for token in cursor.get_tokens()]
                    if '=' not in tokens:
                        tokens = []
                case cindex.CursorKind.TYPE_REF | cindex.CursorKind.TEMPLATE_REF | cindex.CursorKind.NAMESPACE_REF:
                    pass
                case _:
                    logger.debug(f'UNKNOWN {cursor.spelling}: {child.kind}')

        if not tokens:
            return

        return DefaultValue(tokens)

    @property
    def cpp_value(self) -> str:
        index = self.tokens.index('=')
        assert(isinstance(index, int))
        return ' '.join(self.tokens[index + 1:])

    @property
    def py_value(self) -> str:
        index = self.tokens.index('=')
        assert(isinstance(index, int))

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

        equal = self.tokens.index('=')
        return '=' + ''.join(token_filter(t) for t in self.tokens[equal + 1:])

    @property
    def zig_value(self) -> str:
        index = self.tokens.index('=')
        assert(isinstance(index, int))

        def token_filter(src: str) -> str:
            if src[0] == '+':
                src = src[1:]
            if re.match(r'(\d+)?\.(\d+)f$', src):
                src = src[:-1]
            src = src.replace('FLT_MAX', '3.402823466e+38')
            src = src.replace('FLT_MIN', '1.175494351e-38')

            match src:
                case 'NULL' | 'nullptr':
                    return 'null'
                case 'sizeof':
                    return '@sizeOf'
                case 'float':
                    return 'f32'
                case _:
                    return src

        equal = self.tokens.index('=')
        result = ''.join(token_filter(t) for t in self.tokens[equal + 1:])
        if result == 'ImVec2(0,0)':
            return '.{.x=0, .y=0}'

        return result


class ParamContext(TypeContext):
    index: int
    default_value: Optional[DefaultValue]

    def __init__(self, index: int, cursor: cindex.Cursor) -> None:
        super().__init__(cursor.type, cursor)
        self.index = index
        self.default_value = DefaultValue.create(cursor)


class FieldContext(TypeContext):
    index: int

    def __init__(self, index: int, cursor: cindex.Cursor) -> None:
        super().__init__(cursor.type, cursor)
        self.index = index

    @staticmethod
    def get_struct_fields(cursor: cindex.Cursor) -> List['FieldContext']:
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
        return [FieldContext(i, child) for i, child in enumerate(cursors)]


class ResultContext(TypeContext):
    def __init__(self, type: cindex.Type, cursor: cindex.Cursor) -> None:
        super().__init__(type, cursor)
