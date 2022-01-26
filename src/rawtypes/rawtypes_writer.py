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
from .interpreted_types import wrap_types
from .pyi_writer import write_pyi
from . import interpreted_types

logger = logging.getLogger(__name__)

CTYPS_CAST = '''
static PyObject* s_ctypes = nullptr;
static PyObject* s_ctypes_c_void_p = nullptr;
static PyObject* s_ctypes_addressof = nullptr;
static PyObject* s_ctypes_Array = nullptr;
static PyObject* s_ctypes_Structure = nullptr;
static PyObject* s_ctypes_POINTER = nullptr;
static PyObject* s_ctypes__CFuncPtr = nullptr;
static PyObject* s_ctypes_cast = nullptr;
static PyObject* s_value = nullptr;
static std::unordered_map<std::string, PyObject*> s_pydear_ctypes;
static void s_initialize()
{
    if(s_ctypes)
    {
        return;
    }
    // ctypes
    s_ctypes = PyImport_ImportModule("ctypes");
    s_ctypes_c_void_p = PyObject_GetAttrString(s_ctypes, "c_void_p");
    s_ctypes_addressof = PyObject_GetAttrString(s_ctypes, "addressof");
    s_ctypes_Array = PyObject_GetAttrString(s_ctypes, "Array");
    s_ctypes_Structure = PyObject_GetAttrString(s_ctypes, "Structure");
    s_ctypes_POINTER = PyObject_GetAttrString(s_ctypes, "POINTER");
    s_ctypes__CFuncPtr = PyObject_GetAttrString(s_ctypes, "_CFuncPtr");
    s_ctypes_cast = PyObject_GetAttrString(s_ctypes, "cast");
    //
    s_value = PyUnicode_FromString("value");
    //
}

template<typename T>
T ctypes_get_pointer(PyObject *src)
{
    if(!src){
        return (T)nullptr;
    }

    // ctypes.c_void_p
    if(PyObject_IsInstance(src, s_ctypes_c_void_p)){
        if(PyObject *p = PyObject_GetAttr(src, s_value))
        {
            auto pp = PyLong_AsVoidPtr(p);
            Py_DECREF(p);
            return (T)pp;
        }
        PyErr_Clear();
    }

    // ctypes.Array
    // ctypes.Structure
    if(PyObject_IsInstance(src, s_ctypes_Array) || PyObject_IsInstance(src, s_ctypes_Structure) || PyObject_IsInstance(src, s_ctypes__CFuncPtr)){
        if(PyObject *p = PyObject_CallFunction(s_ctypes_addressof, "O", src))
        {
            auto pp = PyLong_AsVoidPtr(p);
            Py_DECREF(p);
            return (T)pp;
        }
PyErr_Print();
        PyErr_Clear();
    }

    return (T)nullptr;
}

static PyObject* GetCTypesType(const char *t, const char *sub)
{
    static std::unordered_map<std::string, PyObject*> s_map;
    {
        auto found = s_map.find(t);
        if(found!=s_map.end())
        {
            return found->second;
        }
    }

    PyObject *p = nullptr;
    {
        auto found = s_pydear_ctypes.find(sub);
        if(found==s_pydear_ctypes.end())
        {
            p = PyImport_ImportModule((std::string("pydear.") + sub).c_str());
            s_pydear_ctypes.insert(std::make_pair(sub, p));
        }
        else{
            p = found->second;
        }
    }

    auto T = PyObject_GetAttrString(p, t);
    auto result = PyObject_CallFunction(s_ctypes_POINTER, "O", T);
    s_map.insert(std::make_pair(std::string(t), result));
    return result;
}

static PyObject* ctypes_cast(PyObject *src, const char *t, const char *sub)
{
    // ctypes.cast(src, ctypes.POINTER(t))[0]
    auto ptype = GetCTypesType(t, sub);
    auto p = PyObject_CallFunction(s_ctypes_cast, "OO", src, ptype);
    Py_DECREF(src);
    auto py_value = PySequence_GetItem(p, 0);
    Py_DECREF(p);
    return py_value;
}

static const char *get_cstring(PyObject *src, const char *default_value)
{
    if(src){
        if(auto p = PyUnicode_AsUTF8(src))
        {
            return p;
        }
        PyErr_Clear();

        if(auto p = PyBytes_AsString(src))
        {
            return p;
        }
        PyErr_Clear();
    }

    return default_value;
}

static PyObject* py_string(const std::string_view &src)
{
    return PyUnicode_FromStringAndSize(src.data(), src.size());
}
'''

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

C_VOID_P = '''
static PyObject* c_void_p(const void* address)
{
    return PyObject_CallFunction(s_ctypes_c_void_p, "K", (uintptr_t)address);
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


def get_params(indent: str, cursor: cindex.Cursor) -> Tuple[List[interpreted_types.basetype.BaseType], str, str, str]:
    sio_extract = io.StringIO()
    sio_cpp_from_py = io.StringIO()
    types = []
    format = ''
    last_format = None
    for i, param in enumerate(TypeWrap.get_function_params(cursor)):
        t = interpreted_types.from_cursor(param.type, param.cursor)
        sio_extract.write(t.cpp_param_declare(indent, i, param.name))
        types.append(t)
        d = param.default_value(use_filter=False)
        if not last_format and d:
            format += '|'
        last_format = d
        format += t.format
        if d:
            d = d.split('=', maxsplit=1)[1]
        sio_cpp_from_py.write(t.cpp_from_py(
            indent, i, d))
    return types, format, sio_extract.getvalue(), sio_cpp_from_py.getvalue()


class PyMethodDef(NamedTuple):
    name: str
    meth: str
    flags: str
    doc: str

    def __str__(self):
        return f'{{"{self.name}", {self.meth}, {self.flags}, "{self.doc}"}}'


def write_function(w: io.IOBase, f: FunctionDecl, overload: str) -> PyMethodDef:
    # signature
    func_name = f'{f.path.stem}_{f.spelling}{overload}'

    namespace = get_namespace(f.cursors)
    result = TypeWrap.from_function_result(f.cursor)
    indent = '  '
    w.write(
        f'static PyObject *{func_name}(PyObject *self, PyObject *args){{\n')

    # prams
    types, format, extract, cpp_from_py = get_params(indent, f.cursor)
    w.write(extract)

    extract_params = ''.join(', &' + t.cpp_extract_name(i)
                             for i, t in enumerate(types))
    w.write(
        f'{indent}if(!PyArg_ParseTuple(args, "{format}"{extract_params})) return NULL;\n')
    w.write(cpp_from_py)

    # call & result
    call_params = ', '.join(t.cpp_call_name(i) for i, t in enumerate(types))
    call = f'{namespace}{f.spelling}({call_params})'
    w.write(interpreted_types.from_cursor(
        result.type, result.cursor).cpp_result(indent, call))

    w.write(f'''}}

''')

    return PyMethodDef(f"{f.spelling}{overload}", func_name, "METH_VARARGS", f"{namespace}{f.spelling}")


def write_method(w: io.IOBase, c: cindex.Cursor,  m: cindex.Cursor) -> PyMethodDef:
    # signature
    func_name = f'{c.spelling}_{m.spelling}'

    # namespace = get_namespace(f.cursors)
    result = TypeWrap.from_function_result(m)
    indent = '  '
    w.write(
        f'static PyObject *{func_name}(PyObject *self, PyObject *args){{\n')

    # prams
    types, format, extract, cpp_from_py = get_params(indent, m)

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
    w.write(interpreted_types.from_cursor(
        result.type, result.cursor).cpp_result(indent, call))

    w.write(f'''}}

''')

    return PyMethodDef(f"{c.spelling}_{m.spelling}", f"{c.spelling}_{m.spelling}", "METH_VARARGS", f"{c.spelling}::{m.spelling}")


def write_ctypes_method(w: io.IOBase, cursor: cindex.Cursor, method: cindex.Cursor, *, pyi=False):
    params = TypeWrap.get_function_params(method)
    result = TypeWrap.from_function_result(method)
    result_t = interpreted_types.from_cursor(result.type, result.cursor)

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


def write_struct(w: io.IOBase, s: StructDecl, flags: wrap_types.WrapFlags) -> Iterable[Tuple[cindex.Cursor, cindex.Cursor]]:
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
            w.write(interpreted_types.from_cursor(
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
            write_ctypes_method(w, cursor, method)
            yield cursor, method

    for code in flags.custom_methods:
        for l in code.splitlines():
            w.write(f'    {l}\n')
        w.write('\n')

    if not fields:  # and not methods and not flags.custom_methods:
        w.write('    pass\n\n')


def write_header(w: io.IOBase, parser: Parser, header: Header, package_dir: pathlib.Path) -> Iterable[PyMethodDef]:
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
        ew.write(wrap_types.IMVECTOR)
        for wrap_type in wrap_types.WRAP_TYPES:
            # structs
            for t in parser.typedef_struct_list:
                if wrap_type.name == t.cursor.spelling:
                    match t:
                        case StructDecl():
                            if t.path != header.path:
                                continue
                            for struct, method in write_struct(ew, t, wrap_type):
                                yield write_method(w, struct, method)

        #
        # enum
        #
        ew.write('from enum import IntEnum\n\n')
        for e in parser.enums:
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

        pyi.write(wrap_types.IMVECTOR)
        write_pyi(header, pyi, parser)

    # functions
    overload_map = {}
    for f in parser.functions:
        if header.path != f.path:
            continue
        if f.is_exclude_function():
            continue

        overload_count = overload_map.get(f.spelling, 0) + 1
        overload_map[f.spelling] = overload_count
        overload = ''
        if overload_count > 1:
            overload += f'_{overload_count}'
        yield write_function(w, f, overload)


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


def write(package_dir: pathlib.Path, parser: Parser, headers: List[Header]) -> pathlib.Path:

    cpp_path = package_dir / 'rawtypes/implmodule.cpp'
    cpp_path.parent.mkdir(parents=True, exist_ok=True)

    with cpp_path.open('w') as w:
        w.write('''// generated
# define PY_SSIZE_T_CLEAN
# ifdef _DEBUG
  # undef _DEBUG
  # include <Python.h>
  # define _DEBUG
  # include <iostream>
# else
  # include <Python.h>
# endif

# include <string>
# include <string_view>
# include <unordered_map>

''')

        w.write(CTYPS_CAST)
        w.write(C_VOID_P)

        modules = []
        for header in headers:
            # separate header to submodule
            info = ModuleInfo(header.path.stem)
            modules.append(info)

            for method in write_header(w, parser, header, package_dir):
                info.functios.append(method)

        w.write(f'''
PyMODINIT_FUNC
PyInit_impl(void)
{{
# ifdef _DEBUG
    std::cout << "DEBUG_BUILD sizeof: ImGuiIO: " << sizeof(ImGuiIO) << std::endl;
# endif

auto __dict__ = PyImport_GetModuleDict();
PyObject *__root__ = nullptr;
{{ // create empty root module
    static PyMethodDef Methods[] = {{
        {{NULL, NULL, 0, NULL}}        /* Sentinel */
    }};

    static struct PyModuleDef module = {{
        PyModuleDef_HEAD_INIT,
        "impl",   /* name of module */
        nullptr, /* module documentation, may be NULL */
        -1,       /* size of per-interpreter state of the module,
                    or -1 if the module keeps state in global variables. */
        Methods
    }};

    __root__ = PyModule_Create(&module);
    if (!__root__){{
        return NULL;
    }}
}}
''')

        for module_info in modules:
            module_info.write_to(w)

        w.write(f'''
    static auto ImplError = PyErr_NewException("impl.error", NULL, NULL);
    Py_XINCREF(ImplError);
    if (PyModule_AddObject(__root__, "error", ImplError) < 0) {{
        Py_XDECREF(ImplError);
        Py_CLEAR(ImplError);
        Py_DECREF(__root__);
        return NULL;
    }}

    s_initialize();

    return __root__;
}}
''')

    return cpp_path
