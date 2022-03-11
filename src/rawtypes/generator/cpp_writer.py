from typing import List, NamedTuple, Optional, Dict
import io
from jinja2 import Environment
from rawtypes.clang import cindex
from rawtypes.interpreted_types import TypeManager
from rawtypes.interpreted_types.basetype import BaseType
from rawtypes.parser.function_cursor import FunctionCursor
from rawtypes.parser.type_context import ParamContext, TypeContext


class ParamInfo(NamedTuple):
    param: ParamContext
    type: BaseType
    default_value: str

    @property
    def index(self) -> int:
        return self.param.index

    @property
    def cpp_param_declare(self) -> str:
        '''
        declara t0.
        PyObject *t0 = NULL;
        '''
        return f'PyObject *t{self.index} = NULL; // {self.type}\n'

    @property
    def cpp_extract_name(self) -> str:
        '''
        load t0.
        &t0
        '''
        return f", &t{self.index}"

    @property
    def cpp_from_py(self) -> str:
        '''
        t0 to p0.
        CXSourceLocation *p0 = ctypes_get_pointer<CXSourceLocation*>(t0);
        '''
        default_value = self.default_value
        if default_value:
            default_value = default_value.split('=', 1)[-1]
        return self.type.cpp_from_py("", self.index, default_value)

    @property
    def cpp_call_name(self) -> str:
        prefix = ''
        if self.index > 0:
            prefix = ', '
        return prefix + self.type.cpp_call_name(self.index)


def to_fromat(params: List[ParamInfo]) -> str:
    formats = []
    last_value = None
    for param in params:
        if not last_value and param.default_value:
            formats.append('|')
        last_value = param.default_value
        formats.append('O')
    return ''.join(formats)


class FunctionCustomization(NamedTuple):
    name: str
    param_override: Dict[str, BaseType]


def to_c_function(env: Environment, function_cursor: FunctionCursor, type_manager: TypeManager, *, namespace: str = '', func_name: str = '', custom: Optional[FunctionCustomization] = None) -> str:
    if not func_name:
        func_name = function_cursor.spelling

    # params
    params = function_cursor.params

    def param_type(param: ParamContext):
        if custom and param.name in custom.param_override:
            return custom.param_override[param.name]
        return type_manager.to_type(param)
    types = [param_type(param) for param in params]
    paramlist = [ParamInfo(param, t, param.default_value.cpp_value if param.default_value else '')
                 for param, t in zip(params, types)]

    # call & result
    result = function_cursor.result
    call_params = ', '.join(t.cpp_call_name(i)
                            for i, t in enumerate(types))
    call = f'{namespace}{function_cursor.spelling}({call_params})'
    result_type = type_manager.from_cursor(result.type, result.cursor)

    template = env.get_template("pycfunc.cpp")
    return template.render(
        cpp_namespace=namespace,
        func_name=func_name,
        params=paramlist,
        format=to_fromat(paramlist),
        call_and_return=result_type.cpp_result('', call)
    )


def to_c_method(env: Environment, c: cindex.Cursor, m: FunctionCursor, type_manager: TypeManager) -> str:
    # signature
    func_name = f'{c.spelling}_{m.spelling}'
    w = io.StringIO()

    # namespace = get_namespace(f.cursors)
    result = m.result
    indent = '  '
    w.write(
        f'static PyObject *{func_name}(PyObject *self, PyObject *args){{\n')

    # prams
    types, format, extract, cpp_from_py = type_manager.get_params(
        indent, m)

    format = 'O' + format

    w.write(f'''{indent}// {c.spelling}
{indent}PyObject *py_this = NULL;
''')
    w.write(extract)

    extract_params = ', &py_this' + ''.join(
        f', &t{i}' for i, t in enumerate(types))
    w.write(
        f'{indent}if(!PyArg_ParseTuple(args, "{format}"{extract_params})) return NULL;\n')

    w.write(
        f'{indent}{c.spelling} *ptr = ctypes_get_pointer<{c.spelling}*>(py_this);\n')
    w.write(cpp_from_py)

    # call & result
    call_params = ', '.join(t.cpp_call_name(i)
                            for i, t in enumerate(types))
    call = f'ptr->{m.spelling}({call_params})'
    w.write(type_manager.from_cursor(
        result.type, result.cursor).cpp_result(indent, call))

    w.write(f'''}}

''')
    return w.getvalue()
