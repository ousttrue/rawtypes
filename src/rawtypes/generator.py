from typing import List
import pathlib
from .header import Header
from .parser import Parser
from . import rawtypes_writer
from .interpreted_types import *


class Generator:
    def __init__(self, *headers: Header) -> None:
        self.headers = list(headers)
        self.parser = Parser([header.path for header in headers])
        self.parser.traverse()
        self.types = TypeRegisteration()

    def generate(self, package_dir: pathlib.Path) -> pathlib.Path:
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

            w.write(rawtypes_writer.CTYPS_CAST)
            w.write(rawtypes_writer.C_VOID_P)

            modules = []
            for header in self.headers:
                # separate header to submodule
                info = rawtypes_writer.ModuleInfo(header.path.stem)
                modules.append(info)

                for method in rawtypes_writer.write_header(w, self, header, package_dir):
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



def generate(headers: List[Header], package_dir: pathlib.Path) -> pathlib.Path:
    generator = Generator(*headers)
    return generator.generate(package_dir)
