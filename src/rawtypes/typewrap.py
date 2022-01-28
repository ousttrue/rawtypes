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


def template_filter(src: str) -> str:
    '''
    replace Some<T> to Some[T]
    '''
    # def rep_typearg(m):
    #     ret = f'[{m.group(0)[1:-1]}]'
    #     return ret
    # dst = TEMPLATE_PATTERN.sub(rep_typearg, src)

    # return dst
    return src.replace('<', '[').replace('>', ']')


class TypeWrap(NamedTuple):
    '''
    function result_type
    function param type
    struct field type
    '''
    type: cindex.Type
    cursor: cindex.Cursor
    namespace: str = 'tinygizmo::'

    def remove_namespce(self, src: str) -> str:
        return src.replace(self.namespace, '')

    @staticmethod
    def from_function_result(cursor: cindex.Cursor):
        return TypeWrap(cursor.result_type, cursor)

    @staticmethod
    def from_function_param(cursor: cindex.Cursor):
        return TypeWrap(cursor.type, cursor)

    @staticmethod
    def get_function_params(cursor: cindex.Cursor):
        return [TypeWrap.from_function_param(child) for child in cursor.get_children() if child.kind == cindex.CursorKind.PARM_DECL]

    @staticmethod
    def from_struct_field(cursor: cindex.Cursor):
        return TypeWrap(cursor.type, cursor)

    @staticmethod
    def get_struct_fields(cursor: cindex.Cursor):
        return [TypeWrap.from_struct_field(child) for child in cursor.get_children(
        ) if child.kind == cindex.CursorKind.FIELD_DECL]

    @staticmethod
    def get_struct_methods(cursor: cindex.Cursor, *, excludes=(), includes=False):
        def method_filter(method: cindex.Cursor) -> bool:
            if method.spelling == 'GetStateStorage':
                pass
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
        for constructor in TypeWrap.get_constructors(cursor):
            params = TypeWrap.get_function_params(constructor)
            if len(params) == 0:
                return constructor

    @property
    def name(self) -> str:
        return symbol_filter(self.cursor.spelling)

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
    def c_type(self) -> str:
        '''
        pxd
        '''
        if self.type.kind == cindex.TypeKind.ENUM:
            return 'int'

        filtered = template_filter(self.type.spelling).replace('[]', '*')
        filtered = filtered.replace('std::string', 'string')
        filtered = filtered.replace('tinygizmo::VertexBuffer', 'VertexBuffer')
        filtered = filtered.replace('uint32_t', 'unsigned int')

        def filter(m):
            return f'{m.group(1)}{m.group(2)}'
        STD_ARRAY_PATTERN = re.compile(r'std::array\[(\w+), (\d+)\]')
        filtered = STD_ARRAY_PATTERN.sub(filter, filtered)

        if 'simple::' in filtered:
            filtered = re.sub(r'simple::Span\[[^\]]+\]', filtered, 'Span')

        if filtered.startswith('std::tuple['):
            return filtered.replace('std::tuple', 'pair')

        return filtered

    @property
    def c_type_with_name(self) -> str:
        '''
        pxd
        '''
        c_type = self.c_type
        name = self.name
        splitted = c_type.split('(*)', maxsplit=1)
        if len(splitted) == 2:
            return f"{splitted[0]}(*{name}){splitted[1]}"
        else:
            return f"{self.remove_namespce(c_type)} {name}"

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
