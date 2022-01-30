from typing import Optional
import dataclasses


class BaseType:
    __match_args__ = ("name", "is_const", "base")

    def __init__(self, name: str, *, is_const: bool = False, base: Optional['BaseType'] = None) -> None:
        self.name = name
        self.is_const = is_const
        self.base = base

    def __eq__(self, __o: object) -> bool:
        match __o:
            case BaseType(name, is_const, base):
                return name == self.name and is_const == self.is_const and base == self.base
        return False

    def __str__(self) -> str:
        return f'{self.__class__.__name__}: {self.name}'

    @property
    def const_prefix(self) -> str:
        is_const = self.is_const
        if self.base and self.base.is_const:
            is_const = True
        return 'const ' if is_const else ''

    @property
    def ctypes_type(self) -> str:
        '''
        ctypes.Structure fields
        '''
        raise NotImplementedError()

    def pyi_field(self, indent: str, name: str) -> str:
        return f'{indent}{name}: {self.ctypes_type} # {self}\n'

    def ctypes_field(self, name: str) -> str:
        return f'("{name}", {self.ctypes_type}), # {self}'

    def param(self, name: str, default_value: str, pyi: bool) -> str:
        '''
        function param
        '''
        raise NotImplementedError()

    def result_typing(self, pyi: bool) -> str:
        '''
        return
        '''
        raise NotImplementedError()

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        '''
        extract params
        '''
        raise NotImplementedError()

    def call_param(self, i: int) -> str:
        return f'p{i}'

    def cdef_result(self, indent: str, call: str) -> str:
        '''
        extract result
        '''
        raise NotImplementedError()

    def cpp_extract_name(self, i: int):
        return f't{i}'

    def cpp_param_declare(self, indent: str, i: int, name) -> str:
        return f'''{indent}// {self}
{indent}PyObject *{self.cpp_extract_name(i)} = NULL;
'''

    @property
    def format(self) -> str:
        return 'O'

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        raise NotImplementedError()

    def cpp_call_name(self, i: int):
        return f'p{i}'

    def py_value(self, value: str):
        raise NotImplementedError()

    def cpp_result(self, indent: str, call: str) -> str:
        return f'''{indent}auto value = {call};
{indent}PyObject* py_value = {self.py_value("value")};
{indent}return py_value;
'''
