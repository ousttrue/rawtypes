from typing import List, Iterable
import pathlib
from jinja2 import Environment, PackageLoader, select_autoescape
from .parser.header import Header
from .parser import Parser
from .interpreted_types import *
from .parser.struct_cursor import StructCursor
from .parser.typedef_cursor import TypedefCursor
from .parser.function_cursor import FunctionCursor, write_pyx_function


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


class Generator:
    def __init__(self, *headers: Header, include_dirs=[]) -> None:
        # parse
        include_dirs = sum(
            [list(header.include_dirs) for header in headers], include_dirs)
        self.parser = Parser(
            [header.path for header in headers],
            include_dirs=include_dirs,
            definitions=sum([list(header.definitions)
                            for header in headers], [])
        )
        self.headers = [
            header for header in headers if not header.include_only]
        self.parser.traverse()
        # prepare
        self.type_manager = TypeManager()
        self.env = Environment(
            loader=PackageLoader("rawtypes"),
        )

    def generate(self, package_dir: pathlib.Path) -> pathlib.Path:

        modules = []
        headers = []
        for header in self.headers:
            #
            # ctypes
            #
            struct_and_methods = []
            with (package_dir / f'{header.path.stem}.py').open('w') as ew:
                ew.write(CTYPES_BEGIN)
                ew.write(f'from .impl.{header.path.stem} import *\n')
                ew.write(header.begin)
                for wrap_type in self.type_manager.WRAP_TYPES:
                    # structs
                    for t in self.parser.typedef_struct_list:
                        if wrap_type.name == t.cursor.spelling:
                            match t:
                                case StructCursor():
                                    if t.path != header.path:
                                        continue
                                    for struct, method in self.write_struct(ew, t, wrap_type):
                                        struct_and_methods.append(
                                            (struct, method))

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
                pyi.write('''import ctypes
from . imgui_enum import *
from typing import Any, Union, Tuple, TYpe, Iterable
''')

                pyi.write(header.begin)
                self.write_pyi(header, pyi)

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
                if f.is_exclude_function():
                    continue
                if not header.if_include(f.spelling):
                    continue

                overload_count = overload_map.get(f.spelling, 0) + 1
                overload_map[f.spelling] = overload_count
                overload = ''
                if overload_count > 1:
                    overload += f'_{overload_count}'
                namespace = get_namespace(f.cursors)
                func_name = f'{f.path.stem}_{f.spelling}{overload}'
                sio.write(f.to_c_function(self.env, self.type_manager,
                          namespace=namespace, func_name=func_name))
                sio.write('\n')
                method = PyMethodDef(
                    f"{f.spelling}{overload}", func_name, "METH_VARARGS", f"{namespace}{f.spelling}")
                methods.append(method)

            for struct, method in struct_and_methods:
                self.write_c_method(sio, struct, method)
                method = PyMethodDef(
                    f"{struct.spelling}_{method.spelling}", f"{struct.spelling}_{method.spelling}", "METH_VARARGS", f"{struct.spelling}::{method.spelling}")
                methods.append(method)

            template = self.env.get_template("module.cpp")
            modules.append(template.render(
                module_name=header.path.stem, methods=methods))
            headers.append(sio.getvalue())

        cpp_path = package_dir / 'rawtypes/implmodule.cpp'
        cpp_path.parent.mkdir(parents=True, exist_ok=True)
        with cpp_path.open('w') as w:
            template = self.env.get_template("impl.cpp")
            w.write(template.render(headers=headers, modules=modules))
        return cpp_path

    def write_struct(self, w: io.IOBase, s: StructCursor, flags: WrapFlags) -> Iterable[Tuple[cindex.Cursor, cindex.Cursor]]:
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
                w.write(self.type_manager.from_cursor(
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
                self.write_ctypes_method(w, cursor, method)
                yield cursor, method

        for code in flags.custom_methods:
            for l in code.splitlines():
                w.write(f'    {l}\n')
            w.write('\n')

        if not fields:  # and not methods and not flags.custom_methods:
            w.write('    pass\n\n')

    def write_c_method(self, w: io.IOBase, c: cindex.Cursor,  m: cindex.Cursor):
        # signature
        func_name = f'{c.spelling}_{m.spelling}'

        # namespace = get_namespace(f.cursors)
        result = TypeWrap.from_function_result(m)
        indent = '  '
        w.write(
            f'static PyObject *{func_name}(PyObject *self, PyObject *args){{\n')

        # prams
        types, format, extract, cpp_from_py = self.type_manager.get_params(
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
        w.write(self.type_manager.from_cursor(
            result.type, result.cursor).cpp_result(indent, call))

        w.write(f'''}}

''')

    def write_pyi(self, header: Header, pyi: io.IOBase):
        types = [x for x in self.parser.typedef_struct_list if pathlib.Path(
            x.cursor.location.file.name) == header.path]
        if types:
            for v in self.type_manager.WRAP_TYPES:
                for typedef_or_struct in types:
                    if typedef_or_struct.cursor.spelling == v.name:
                        match typedef_or_struct:
                            case TypedefCursor():
                                typedef_or_struct.write_pyi(
                                    pyi, flags=v)
                            case StructCursor():
                                typedef_or_struct.write_pyi(
                                    self.type_manager, pyi, flags=v)
                            case _:
                                raise Exception()

        funcs = [x for x in self.parser.functions if pathlib.Path(
            x.cursor.location.file.name) == header.path]
        if funcs:
            overload = {}
            for typedef_or_struct in funcs:
                if typedef_or_struct.is_exclude_function():
                    continue

                name = typedef_or_struct.spelling
                count = overload.get(name, 0) + 1
                write_pyx_function(
                    self.type_manager, pyi, typedef_or_struct.cursor, pyi=True, overload=count, prefix=header.prefix)
                overload[name] = count

    def write_ctypes_method(self, w: io.IOBase, cursor: cindex.Cursor, method: cindex.Cursor, *, pyi=False):
        params = TypeWrap.get_function_params(method)
        result = TypeWrap.from_function_result(method)
        result_t = self.type_manager.from_cursor(result.type, result.cursor)

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


def generate(headers: List[Header], package_dir: pathlib.Path) -> pathlib.Path:
    generator = Generator(*headers)
    return generator.generate(package_dir)
