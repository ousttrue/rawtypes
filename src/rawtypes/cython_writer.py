from typing import Tuple, List
import io
import pathlib
from rawtypes.clang import cindex
from .header import Header
from .parser import Parser
from .declarations import function
from .interpreted_types import wrap_types
from .pyi_writer import write_pyi

STD_ARRAY = '''
cdef extern from "<array>" namespace "std" nogil:
  cdef cppclass float2 "std::array<float, 2>":
    float2() except+
    float& operator[](size_t)
cdef extern from "<array>" namespace "std" nogil:
  cdef cppclass float3 "std::array<float, 3>":
    float3() except+
    float& operator[](size_t)
cdef extern from "<array>" namespace "std" nogil:
  cdef cppclass float4 "std::array<float, 4>":
    float4() except+
    float& operator[](size_t)

'''

PXD_SPAN = '''
cdef struct Span:
    void *_data
    size_t count

'''


def get_namespace(cursors: Tuple[cindex.Cursor, ...]) -> str:
    namespaces = [cursor for cursor in cursors if cursor.kind ==
                  cindex.CursorKind.NAMESPACE]
    if not namespaces:
        return ''
    return '.'.join(namespace.spelling for namespace in namespaces)


def enter_namespace(header: Header, pxd: io.IOBase, cursors: Tuple[cindex.Cursor, ...]):
    namespace = get_namespace(cursors)
    if namespace == header.current_nemespace:
        return

    if namespace:
        pxd.write(
            f'cdef extern from "{header.path.name}" namespace "{namespace}":\n')
    else:
        pxd.write(
            f'cdef extern from "{header.path.name}":\n')
    header.current_nemespace = namespace


def write_pxd(header: Header, pxd: io.IOBase, parser: Parser):
    header.current_nemespace = None

    # enum
    for enum in parser.enums:
        if pathlib.Path(enum.cursor.location.file.name) != header.path:
            continue
        enter_namespace(header, pxd, enum.cursors)
        pxd.write(f'    ctypedef enum {enum.cursor.spelling}:\n')
        pxd.write(f'        pass\n')

    # typedef & struct
    for t in parser.typedef_struct_list:
        if pathlib.Path(t.cursor.location.file.name) != header.path:
            continue
        if t.cursor.spelling in function.EXCLUDE_TYPES:
            # TODO: nested type
            continue

        enter_namespace(header, pxd, t.cursors)
        t.write_pxd(pxd, excludes=function.EXCLUDE_TYPES)

    # funcs
    for func in parser.functions:
        if pathlib.Path(func.cursor.location.file.name) != header.path:
            continue
        enter_namespace(header, pxd, func.cursors)
        if func.is_exclude_function():
            continue
        function.write_pxd_function(pxd, func.cursor)


def write_pyx(header: Header, pyx: io.IOBase, parser: Parser):
    types = [x for x in parser.typedef_struct_list if pathlib.Path(
        x.cursor.location.file.name) == header.path]
    if types:
        for v in wrap_types.WRAP_TYPES:
            for func in types:
                if func.cursor.spelling == v.name:
                    func.write_pyx_ctypes(pyx, flags=v)

    funcs = [x for x in parser.functions if pathlib.Path(
        x.cursor.location.file.name) == header.path]
    if funcs:
        overload = {}
        for func in funcs:
            if func.is_exclude_function():
                continue

            name = func.spelling
            count = overload.get(name, 0) + 1
            function.write_pyx_function(
                pyx, func.cursor, overload=count, prefix=header.prefix)
            overload[name] = count


def write(package_dir: pathlib.Path, parser: Parser, headers: List[Header]):
    ext_dir = package_dir / 'impl'
    if ext_dir.exists():
        import shutil
        shutil.rmtree(ext_dir, ignore_errors=True)
    ext_dir.mkdir(parents=True, exist_ok=True)

    #
    # pxd
    #
    with (ext_dir / 'impl.pxd').open('w') as pxd:
        pxd.write(f'''from libcpp cimport bool
from libcpp.string cimport string
from libcpp.pair cimport pair

''')

        pxd.write(STD_ARRAY)
        pxd.write(PXD_SPAN)
        for header in headers:
            write_pxd(header, pxd, parser)

    #
    # pyx
    #
    with (ext_dir / 'impl.pyx').open('w') as pyx:
        pyx.write('''from typing import Tuple, Any, Union, Iterable, Type
import ctypes
from libcpp cimport bool
from libcpp.string cimport string
from libcpp.pair cimport pair
from libc.stdint cimport uintptr_t
from libc.string cimport memcpy 
cimport impl

''')
        pyx.write(wrap_types.IMVECTOR)
        pyx.write(STD_ARRAY)
        for header in headers:
            write_pyx(header, pyx, parser)

    #
    # pyi
    #
    pyi_path = package_dir / '__init__.pyi'
    with pyi_path.open('w') as pyi:
        pyi.write('''import ctypes
from . imgui_enum import *
from typing import Any, Union, Tuple
''')

        pyi.write(wrap_types.IMVECTOR)
        for header in headers:
            write_pyi(header, pyi, parser)
