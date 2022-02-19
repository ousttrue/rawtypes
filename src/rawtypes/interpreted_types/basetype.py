

class BaseType:
    '''
    コード生成時の型ごとの変換ルールを定義する。

    Extension を実装する c/c++ の表現、
    ctypes.Structure のフィールド表現、
    language-server 向けの pyi 表現をサポートする。

    それぞれについて、関数の引数、返り値、Structのフィールドのコンテキストがある。
    `c/c++` に関しては、
    `PyObjct*` 型のローカル変数への展開、
    `PyObjct*` 型のローカル変数から `c/c++` の値の取り出し、
    取り出した変数を用いた関数呼び出し、
    `void` 以外の関数の実行結果を `PyObject*` にパックする追加のコンテキストがある。
    '''
    __match_args__ = ("name", "is_const")

    def __init__(self, name: str, is_const: bool = False) -> None:
        self.name = name
        self.is_const = is_const

    def __eq__(self, __o: object) -> bool:
        match __o:
            case BaseType(name, is_const):
                return name == self.name and is_const == self.is_const
        return False

    def __str__(self) -> str:
        return f'{self.__class__.__name__}: {self.name}'

    @property
    def ctypes_type(self) -> str:
        '''
        ctypes.Structure fields
        '''
        raise NotImplementedError()

    def ctypes_field(self, name: str) -> str:
        '''
        ctypes.Structure の _field_ の中身。
        '''
        return f'("{name}", {self.ctypes_type}), # {self}'

    @property
    def pyi_type(self) -> str:
        '''
        language-server でエラー表示になるのを回避する

        ex: ctypes.c_int32 => int
        '''
        return self.ctypes_type

    def pyi_field(self, indent: str, name: str) -> str:
        '''
        pyi のフィールド
        '''
        return f'{indent}{name}: {self.pyi_type} # {self}'

    def py_param(self, name: str, default_value: str, pyi: bool) -> str:
        raise NotImplementedError()

    @property
    def py_result(self) -> str:
        return self.pyi_type

    @property
    def const_prefix(self) -> str:
        '''
        ex: const char *
        '''
        return 'const ' if self.is_const else ''

    @property
    def PyArg_ParseTuple_format(self) -> str:
        return 'O'

    def cpp_from_py(self, indent: str, i: int, default_value: str) -> str:
        '''
        PyObject* から c/c++ の値を取り出す
        '''
        raise NotImplementedError()

    def cpp_call_name(self, i: int):
        return f'p{i}'

    def cpp_to_py(self, value: str):
        '''
        c/c++ の値から PyObject* を作る
        '''
        raise NotImplementedError()

    def cpp_result(self, indent: str, call: str) -> str:
        '''
        c/c++ の関数を呼び出す。
        結果から PyObject* を作って返す。
        '''
        return f'''{indent}auto value = {call};
{indent}PyObject* py_value = {self.cpp_to_py("value")};
{indent}return py_value;
'''
