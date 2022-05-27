from typing import List, Tuple, NamedTuple
import io
import shutil
import pathlib
import pkg_resources
from rawtypes.generator.cpp_writer import to_c_function, to_c_method
from rawtypes.generator.py_writer import to_ctypes_iter, write_pyi_function, write_pyi_struct
from ..parser.header import Header
from ..parser import Parser
from ..interpreted_types import *
from ..parser.struct_cursor import StructCursor, WrapFlags
from ..parser.typedef_cursor import TypedefCursor
from ..parser.function_cursor import FunctionCursor
from .generator_base import GeneratorBase


PY_BEGIN = '''from typing import Type, Tuple, Union, Any, Iterable
import ctypes
from enum import IntEnum
'''


def get_namespace(cursors: Tuple[cindex.Cursor, ...]) -> str:
    sio = io.StringIO()
    for cursor in cursors:
        if cursor.kind == cindex.CursorKind.NAMESPACE:  # type: ignore
            sio.write(f'{cursor.spelling}::')
    return sio.getvalue()


class PyMethodDef(NamedTuple):
    name: str
    meth: str
    flags: str
    doc: str

    def __str__(self):
        return f'{{"{self.name}", {self.meth}, {self.flags}, "{self.doc}"}}'


class PythonGenerator(GeneratorBase):
    def __init__(self, *headers: Header, include_dirs=[], target='') -> None:
        super().__init__(*headers, use_typdef=False,
                         include_dirs=include_dirs, target=target)

    def generate(self, package_dir: pathlib.Path, cpp_path: pathlib.Path, *, function_custom=[], is_exclude_function=None):

        modules = []
        headers = []
        for header in self.headers:
            #
            # ctypes
            #
            structs: List[Tuple[StructCursor, WrapFlags]] = []

            with (package_dir / f'{header.path.stem}.py').open('w') as ew:
                ew.write(PY_BEGIN)
                ew.write(f'from .impl.{header.path.stem} import *\n')
                ew.write(header.begin)
                for wrap_type in self.type_manager.WRAP_TYPES:
                    # structs
                    for t in self.parser.typedef_struct_list:
                        if wrap_type.name == t.cursor.spelling:
                            match t:
                                case StructCursor() as s:
                                    if s.path != header.path:
                                        continue
                                    if s.is_forward_decl:
                                        continue
                                    for py in to_ctypes_iter(self.env, s, wrap_type, self.type_manager):
                                        ew.write(py)
                                    structs.append((s, wrap_type))

                # enum
                ew.write('from enum import IntEnum\n\n')
                for e in self.parser.enums:
                    if e.path != header.path:
                        continue
                    e.write_to(ew)

            #
            # pyi
            #
            with (package_dir / f'{header.path.stem}.pyi').open('w') as pyi:
                pyi.write(PY_BEGIN)
                pyi.write(header.begin)
                self.write_pyi(
                    header, pyi, is_exclude_function=is_exclude_function)

                # enum
                pyi.write('from enum import IntEnum\n\n')
                for e in self.parser.enums:
                    if e.path != header.path:
                        continue
                    e.write_to(pyi)

            #
            # cpp
            #
            sio = io.StringIO()
            sio.write(header.before_include)
            sio.write(f'# include <{header.path.name}>\n')
            sio.write(header.after_include)

            methods = []
            overload_map = {}
            for f in self.parser.functions:
                if header.path != f.path:
                    continue
                if is_exclude_function and is_exclude_function(f):
                    continue
                if not header.if_include(f.spelling):
                    continue

                customize = None
                for custom in function_custom:
                    if custom.name == f.spelling:
                        customize = custom
                        break

                overload_count = overload_map.get(f.spelling, 0) + 1
                overload_map[f.spelling] = overload_count
                overload = ''
                if overload_count > 1:
                    overload += f'_{overload_count}'
                namespace = get_namespace(f.cursors)
                func_name = f'{f.path.stem}_{f.spelling}{overload}'
                sio.write(to_c_function(self.env, f, self.type_manager,
                          namespace=namespace, func_name=func_name, custom=customize))
                sio.write('\n')
                method = PyMethodDef(
                    f"{f.spelling}{overload}", func_name, "METH_VARARGS", f"{namespace}{f.spelling}")
                methods.append(method)

            if header.additional_functions:
                for k, v in header.additional_functions.items():
                    sio.write(v)
                    method = PyMethodDef(
                        k, k, "METH_VARARGS", f"additional: {k}")
                    methods.append(method)

            for struct, wrap_type in structs:
                for method in struct.get_methods(wrap_type):
                    sio.write(to_c_method(self.env, struct.cursor,
                              method, self.type_manager))
                    method = PyMethodDef(
                        f"{struct.spelling}_{method.spelling}", f"{struct.spelling}_{method.spelling}", "METH_VARARGS", f"{struct.spelling}::{method.spelling}")
                    methods.append(method)

            template = self.env.get_template("module.cpp")
            modules.append(template.render(
                module_name=header.path.stem, methods=methods))
            headers.append(sio.getvalue())

        # __init__.py
        with (package_dir / '__init__.py').open('w') as w:
            # empty ok
            pass

        cpp_path.parent.mkdir(parents=True, exist_ok=True)
        with cpp_path.open('w') as w:
            template = self.env.get_template("impl.cpp")
            w.write(template.render(headers=headers, modules=modules))

        # copy rawtypes.h
        RAWTYPES_H = pathlib.Path(pkg_resources.resource_filename(
            'rawtypes.generator', 'templates/rawtypes.h'))
        shutil.copy(RAWTYPES_H, cpp_path.parent / RAWTYPES_H.name)

    def write_pyi(self, header: Header, pyi: io.IOBase, is_exclude_function):
        types = [x for x in self.parser.typedef_struct_list if pathlib.Path(
            x.cursor.location.file.name) == header.path]
        if types:
            for v in self.type_manager.WRAP_TYPES:
                for f in types:
                    if f.cursor.spelling == v.name:
                        match f:
                            case TypedefCursor():
                                pass
                            case StructCursor():
                                write_pyi_struct(
                                    f, self.type_manager, pyi, flags=v)
                            case _:
                                raise Exception()

        funcs = [x for x in self.parser.functions if pathlib.Path(
            x.cursor.location.file.name) == header.path]
        if funcs:
            overload = {}
            for f in funcs:
                if is_exclude_function and is_exclude_function(f):
                    continue

                name = f.spelling
                count = overload.get(name, 0) + 1
                write_pyi_function(
                    self.type_manager, pyi, f.cursor, overload=count, prefix=header.prefix)
                overload[name] = count
