from typing import List, Tuple, Iterable, Optional, NamedTuple
import logging
import io
import pathlib
#
from rawtypes.clang import cindex
#
from .parser import Parser
from .header import Header
from .declarations.typewrap import TypeWrap
from .declarations.function import FunctionDecl
from .declarations.struct import StructDecl
from .interpreted_types import wrap_types, WrapFlags
from .pyi_writer import write_pyi
from . import interpreted_types

logger = logging.getLogger(__name__)


IMGUI_TYPE = '''
static ImVec2 get_ImVec2(PyObject *src)
{
    float x, y;
    if(PyArg_ParseTuple(src, "ff", &x, &y))
    {
        return {x, y};
    }
    PyErr_Clear();

    return {};
}
'''


CTYPES_BEGIN = '''from typing import Iterable, Type, Tuple
import ctypes
from enum import IntEnum
'''


def get_namespace(cursors: Tuple[cindex.Cursor, ...]) -> str:
    sio = io.StringIO()
    for cursor in cursors:
        if cursor.kind == cindex.CursorKind.NAMESPACE:
            sio.write(f'{cursor.spelling}::')
    return sio.getvalue()


class PyMethodDef(NamedTuple):
    name: str
    meth: str
    flags: str
    doc: str

    def __str__(self):
        return f'{{"{self.name}", {self.meth}, {self.flags}, "{self.doc}"}}'


def write_function(w: io.IOBase, type_map, f: FunctionDecl, overload: str) -> PyMethodDef:
    # signature
    func_name = f'{f.path.stem}_{f.spelling}{overload}'

    namespace = get_namespace(f.cursors)
    result = TypeWrap.from_function_result(f.cursor)
    indent = '  '
    w.write(
        f'static PyObject *{func_name}(PyObject *self, PyObject *args){{\n')

    # prams
    types, format, extract, cpp_from_py = type_map.get_params(indent, f.cursor)
    w.write(extract)

    extract_params = ''.join(', &' + t.cpp_extract_name(i)
                             for i, t in enumerate(types))
    w.write(
        f'{indent}if(!PyArg_ParseTuple(args, "{format}"{extract_params})) return NULL;\n')
    w.write(cpp_from_py)

    # call & result
    call_params = ', '.join(t.cpp_call_name(i) for i, t in enumerate(types))
    call = f'{namespace}{f.spelling}({call_params})'
    w.write(type_map.from_cursor(
        result.type, result.cursor).cpp_result(indent, call))

    w.write(f'''}}

''')

    return PyMethodDef(f"{f.spelling}{overload}", func_name, "METH_VARARGS", f"{namespace}{f.spelling}")


def write_method(w: io.IOBase, type_map: interpreted_types.TypeManager, c: cindex.Cursor,  m: cindex.Cursor) -> PyMethodDef:
    # signature
    func_name = f'{c.spelling}_{m.spelling}'

    # namespace = get_namespace(f.cursors)
    result = TypeWrap.from_function_result(m)
    indent = '  '
    w.write(
        f'static PyObject *{func_name}(PyObject *self, PyObject *args){{\n')

    # prams
    types, format, extract, cpp_from_py = type_map.get_params(indent, m)

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
    call_params = ', '.join(t.cpp_call_name(i) for i, t in enumerate(types))
    call = f'ptr->{m.spelling}({call_params})'
    w.write(type_map.from_cursor(
        result.type, result.cursor).cpp_result(indent, call))

    w.write(f'''}}

''')

    return PyMethodDef(f"{c.spelling}_{m.spelling}", f"{c.spelling}_{m.spelling}", "METH_VARARGS", f"{c.spelling}::{m.spelling}")


def write_ctypes_method(w: io.IOBase, types: interpreted_types.TypeManager, cursor: cindex.Cursor, method: cindex.Cursor, *, pyi=False):
    params = TypeWrap.get_function_params(method)
    result = TypeWrap.from_function_result(method)
    result_t = types.from_cursor(result.type, result.cursor)

    # signature
    w.write(
        f'    def {method.spelling}(self, *args)')
    w.write(f'->{result_t.result_typing(pyi=pyi)}:')

    if pyi:
        w.write(' ...\n')
        return

    w.write('\n')

    indent = '        '

    w.write(f'{indent}from .impl import imgui\n')
    w.write(
        f'{indent}return imgui.{cursor.spelling}_{method.spelling}(self, *args)\n')


def write_struct(w: io.IOBase, types: interpreted_types.TypeManager, s: StructDecl, flags: WrapFlags) -> Iterable[Tuple[cindex.Cursor, cindex.Cursor]]:
    cursor = s.cursors[-1]

    definition = cursor.get_definition()
    if definition and definition != cursor:
        # skip forward decl
        return

    w.write(f'class {cursor.spelling}(ctypes.Structure):\n')
    fields = TypeWrap.get_struct_fields(cursor) if flags.fields else []
    if fields:
        w.write('    _fields_=[\n')
        indent = '        '
        for field in fields:
            name = field.name
            if flags.custom_fields.get(name):
                name = '_' + name
            w.write(types.from_cursor(
                field.cursor.type, field.cursor).ctypes_field(indent, name))
        w.write('    ]\n\n')

#     if flags.default_constructor:
#         constructor = TypeWrap.get_default_constructor(cursor)
#         if constructor:
#             w.write(f'''    def __init__(self, **kwargs):
#     p = new impl.{cursor.spelling}()
#     memcpy(<void *><uintptr_t>ctypes.addressof(self), p, sizeof(impl.{cursor.spelling}))
#     del p
#     super().__init__(**kwargs)

# ''')

    for _, v in flags.custom_fields.items():
        w.write('    @property\n')
        for l in v.splitlines():
            w.write(f'    {l}\n')
        w.write('\n')

    methods = TypeWrap.get_struct_methods(cursor, includes=flags.methods)
    if methods:
        for method in methods:
            write_ctypes_method(w, types, cursor, method)
            yield cursor, method

    for code in flags.custom_methods:
        for l in code.splitlines():
            w.write(f'    {l}\n')
        w.write('\n')

    if not fields:  # and not methods and not flags.custom_methods:
        w.write('    pass\n\n')


def write_header(w: io.IOBase, generator, header: Header, package_dir: pathlib.Path) -> Iterable[PyMethodDef]:
    w.write(f'''
# include <{header.path.name}>

''')
    if header.path.name == 'imgui.h':
        w.write(IMGUI_TYPE)

    #
    # ctypes
    #
    with (package_dir / f'{header.path.stem}.py').open('w') as ew:
        ew.write(CTYPES_BEGIN)
        ew.write(f'from .impl.{header.path.stem} import *\n')
        ew.write(header.begin)
        for wrap_type in generator.types.WRAP_TYPES:
            # structs
            for t in generator.parser.typedef_struct_list:
                if wrap_type.name == t.cursor.spelling:
                    match t:
                        case StructDecl():
                            if t.path != header.path:
                                continue
                            for struct, method in write_struct(ew, generator.types, t, wrap_type):
                                yield write_method(w, generator.types, struct, method)

        #
        # enum
        #
        ew.write('from enum import IntEnum\n\n')
        for e in generator.parser.enums:
            if e.path != header.path:
                continue
            e.write_to(ew)

    #
    # pyi
    #
    with (package_dir / f'{header.path.stem}.pyi').open('w') as pyi:
        pyi.write('''import ctypes
from . imgui_enum import *
from typing import Any, Union, Tuple, TYpe, Iterable
''')

        pyi.write(header.begin)
        write_pyi(header, generator, pyi)

    # functions
    overload_map = {}
    for f in generator.parser.functions:
        if header.path != f.path:
            continue
        if f.is_exclude_function():
            continue

        overload_count = overload_map.get(f.spelling, 0) + 1
        overload_map[f.spelling] = overload_count
        overload = ''
        if overload_count > 1:
            overload += f'_{overload_count}'
        yield write_function(w, generator.types, f, overload)


class ModuleInfo:
    def __init__(self, name) -> None:
        self.name = name
        self.functios = []

    def write_to(self, w: io.IOBase):
        sio = io.StringIO()
        for func in self.functios:
            sio.write(f'    {func},\n')
        w.write(f'''
{{ // {self.name}
    static PyMethodDef Methods[] = {{
    {sio.getvalue()}
        {{NULL, NULL, 0, NULL}}        /* Sentinel */
    }};

    static struct PyModuleDef module = {{
        PyModuleDef_HEAD_INIT,
        "{self.name}",   /* name of module */
        nullptr, /* module documentation, may be NULL */
        -1,       /* size of per-interpreter state of the module,
                    or -1 if the module keeps state in global variables. */
        Methods
    }};

    auto m = PyModule_Create(&module);
    assert(m);
    // if (!m){{
    //     return NULL;
    // }}

    // add submodule
    PyDict_SetItemString(__dict__, "pydear.impl.{self.name}", m);
}}
''')
