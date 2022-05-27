from typing import List, Optional, NamedTuple, Callable
import io
import re
from ..clang import cindex
from ..parser.type_context import TypeContext
from ..parser.struct_cursor import WrapFlags
from ..parser.function_cursor import FunctionCursor
from .basetype import BaseType
from .definition import StructType, TypedefType, EnumType
from .function_types import FunctionProto
from .pointer_types import PointerType, ReferenceType, ArrayType, ReferenceToStdArrayType
from .string_types import CppStringType, CStringType, CharPointerType
from .wrap_types import PointerToStructType, ReferenceToStructType
from . import primitive_types

STD_ARRAY = re.compile(r'(const )?std::array<(\w+), (\d+)> &')


class TypeWithCursor(NamedTuple):
    type: cindex.Type
    cursor: cindex.Cursor

    def __str__(self) -> str:
        return f'{self.type.spelling}'

    @property
    def spelling(self) -> str:
        return self.type.spelling

    def ref_from_children(self) -> Optional[cindex.Cursor]:
        try:
            return next(iter(
                c for c in self.cursor.get_children() if c.kind == cindex.CursorKind.TYPE_REF))
        except:
            pass

    @property
    def underlying(self) -> Optional['TypeWithCursor']:
        if self.type.kind != cindex.TypeKind.TYPEDEF:
            return

        ref = self.ref_from_children()
        assert(ref)
        if ref:
            assert ref.referenced.kind == cindex.CursorKind.TYPEDEF_DECL
            underlying_type = ref.referenced.underlying_typedef_type

            return TypeWithCursor(underlying_type, ref.referenced)


class TypeProcessor(NamedTuple):
    process: Callable[[TypeWithCursor], Optional[BaseType]]


class Params(NamedTuple):
    types: List[BaseType]
    format: str
    extract: str
    from_py: str


class TypeManager:
    def __init__(self, use_typedef=True) -> None:
        self.WRAP_TYPES: List[WrapFlags] = []
        self.processors: List[TypeProcessor] = []
        self.use_typedef = use_typedef

    def get_wrap_type(self, name: str) -> Optional[WrapFlags]:
        if name.startswith('struct '):
            # for C struct without typedef
            name = name[7:]
        for w in self.WRAP_TYPES:
            if w.name == name and w.fields:
                return w

    def get(self, c: TypeWithCursor, is_const=False) -> BaseType:
        is_const = is_const or c.type.is_const_qualified()
        for t in self.processors:
            value = t.process(c)
            if value:
                return value

        m = STD_ARRAY.match(c.spelling)
        if m:
            is_const = True if m.group(1) else False
            base = primitive_types.get(m.group(2), False)
            return ReferenceToStdArrayType(base, int(m.group(3)), is_const=is_const)

        match c.spelling:
            case 'std::string' | 'const std::string &':
                return CppStringType()
            case 'const char *':
                return CStringType()
            case 'size_t':
                return primitive_types.SizeType()

        match c.type.kind:
            case cindex.TypeKind.VOID:
                return primitive_types.VoidType(is_const)

            case cindex.TypeKind.BOOL:
                return primitive_types.BoolType(is_const)

            case cindex.TypeKind.CHAR_S | cindex.TypeKind.SCHAR:  # type: ignore
                return primitive_types.Int8Type(is_const)
            case cindex.TypeKind.SHORT:
                return primitive_types.Int16Type(is_const)
            case cindex.TypeKind.INT:
                return primitive_types.Int32Type(is_const)
            case cindex.TypeKind.LONGLONG:
                return primitive_types.Int64Type(is_const)

            case cindex.TypeKind.UCHAR:
                return primitive_types.UInt8Type(is_const)
            case cindex.TypeKind.USHORT:
                return primitive_types.UInt16Type(is_const)
            case cindex.TypeKind.UINT:
                return primitive_types.UInt32Type(is_const)
            case cindex.TypeKind.ULONGLONG:
                return primitive_types.UInt64Type(is_const)

            case cindex.TypeKind.FLOAT:
                return primitive_types.FloatType(is_const)
            case cindex.TypeKind.DOUBLE:
                return primitive_types.DoubleType(is_const)

            case cindex.TypeKind.POINTER:
                pointee = c.type.get_pointee()
                base = self.get(TypeWithCursor(pointee, c.cursor))
                if isinstance(base, StructType) and any(t for t in self.WRAP_TYPES if t.name == base.name):
                    return PointerToStructType(base, is_const=is_const, wrap_type=self.get_wrap_type(base.name), )

                return PointerType(base, is_const=is_const)

            case cindex.TypeKind.LVALUEREFERENCE:
                pointee = c.type.get_pointee()
                base = self.get(TypeWithCursor(pointee, c.cursor))
                if isinstance(base, StructType) and any(t for t in self.WRAP_TYPES if t.name == base.name):
                    return ReferenceToStructType(base, is_const=is_const, wrap_type=self.get_wrap_type(base.name))

                return ReferenceType(base, is_const=is_const)

            case cindex.TypeKind.INCOMPLETEARRAY:
                element = c.type.get_array_element_type()
                base = self.get(TypeWithCursor(element, c.cursor))
                return PointerType(base, is_const=is_const)

            case cindex.TypeKind.CONSTANTARRAY:
                element = c.type.get_array_element_type()
                base = self.get(TypeWithCursor(element, c.cursor))
                return ArrayType(base, c.type.get_array_size(), is_const=is_const)

            case cindex.TypeKind.TYPEDEF:
                underlying = c.underlying
                assert(underlying)
                if self.use_typedef:
                    return TypedefType(c.spelling, self.get(underlying, is_const), is_const=is_const)
                else:
                    return self.get(underlying, is_const)

            case cindex.TypeKind.RECORD:
                deref = c.ref_from_children()
                if deref:
                    assert deref.referenced.kind == cindex.CursorKind.STRUCT_DECL
                    return StructType(deref.referenced.spelling, deref.referenced, is_const=is_const, wrap_type=self.get_wrap_type(c.type.spelling))

                # inline decl or anonymous
                return StructType(c.cursor.spelling, c.cursor, is_const=is_const, nested_type=c.cursor)

            case cindex.TypeKind.FUNCTIONPROTO:
                return FunctionProto(FunctionCursor(c.type.get_result(), (c.cursor,)))

            case cindex.TypeKind.ENUM:
                return EnumType(c.type.spelling)

            case cindex.TypeKind.ELABORATED:
                return StructType(c.type.spelling, c.cursor, is_const=is_const, wrap_type=self.get_wrap_type(c.type.spelling))

            case cindex.TypeKind.UNEXPOSED:
                # template ?
                if c.type.spelling[-1] == '>':
                    return StructType(c.type.spelling, c.cursor, is_const=is_const, wrap_type=self.get_wrap_type(c.type.spelling))

        raise RuntimeError(f"unknown type: {c.cursor.location} {c.type.kind}")

    def from_cursor(self, cursor_type: cindex.Type, cursor: cindex.Cursor) -> BaseType:
        return self.get(TypeWithCursor(cursor_type, cursor))

    def to_type(self, typewrap: TypeContext) -> BaseType:
        return self.from_cursor(typewrap.type, typewrap.cursor)

    def get_params(self, indent: str, f: FunctionCursor) -> Params:
        sio_extract = io.StringIO()
        sio_cpp_from_py = io.StringIO()
        types = []
        format = ''
        last_format = None
        for param in f.params:
            t = self.from_cursor(param.type, param.cursor)
            sio_extract.write(f'PyObject *t{param.index} = NULL;\n')
            types.append(t)
            d = param.default_value
            if not last_format and d:
                format += '|'
            last_format = d
            format += t.PyArg_ParseTuple_format
            sio_cpp_from_py.write(t.cpp_from_py(
                indent, param.index, d.cpp_value if d else ''))
        return Params(types, format, sio_extract.getvalue(), sio_cpp_from_py.getvalue())
