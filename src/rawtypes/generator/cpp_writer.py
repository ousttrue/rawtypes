
from jinja2 import Environment
from rawtypes.interpreted_types import TypeManager
from rawtypes.parser.function_cursor import FunctionCursor


def to_c_function(function_cursor: FunctionCursor, env: Environment, type_manager: TypeManager, *, namespace: str = '', func_name: str = '') -> str:
    if not func_name:
        func_name = function_cursor.spelling

    result = function_cursor.result
    indent = '  '
    # prams
    types, format, extract, cpp_from_py = type_manager.get_params(
        indent, function_cursor)
    extract_params = ''.join(', &' + t.cpp_extract_name(i)
                             for i, t in enumerate(types))

    # call & result
    call_params = ', '.join(t.cpp_call_name(i)
                            for i, t in enumerate(types))
    call = f'{namespace}{function_cursor.spelling}({call_params})'
    result_type = type_manager.from_cursor(result.type, result.cursor)

    template = env.get_template("pycfunc.cpp")
    return template.render(
        func_name=func_name,
        extract=extract,
        format=format,
        extract_params=extract_params,
        cpp_from_py=cpp_from_py,
        result=result_type.cpp_result(indent, call)
    )
