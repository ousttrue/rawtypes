from typing import List, NamedTuple
import io
from jinja2 import Environment
from rawtypes.clang import cindex
from rawtypes.interpreted_types import TypeManager
from rawtypes.interpreted_types.basetype import BaseType
from rawtypes.parser.function_cursor import FunctionCursor
from rawtypes.parser.typewrap import TypeWrap


class ParamInfo(NamedTuple):
    index: int
    param: TypeWrap
    type: BaseType
    default_value: str

    @property
    def cpp_param_declare(self) -> str:
        '''
        declara t0.
        PyObject *t0 = NULL;
        '''
        return self.type.cpp_param_declare('', self.index, self.param.name)

    @property
    def cpp_extract_name(self) -> str:
        '''
        load t0.
        &t0
        '''
        return ", &" + self.type.cpp_extract_name(self.index)

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


def to_c_function(function_cursor: FunctionCursor, env: Environment, type_manager: TypeManager, *, namespace: str = '', func_name: str = '') -> str:
    if not func_name:
        func_name = function_cursor.spelling

    # params
    params = function_cursor.params
    types = [type_manager.to_type(param) for i, param in params]
    paramlist = [ParamInfo(i, param, t, param.default_value(
        use_filter=False)) for (i, param), t in zip(params, types)]

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


def to_c_method(c: cindex.Cursor, m: FunctionCursor, env: Environment, type_manager: TypeManager) -> str:
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

    extract_params = ', &py_this' + ''.join(', &' + t.cpp_extract_name(i)
                                            for i, t in enumerate(types))
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
