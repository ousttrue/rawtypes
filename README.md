# rawtypes

A code generator using libclang for a python extension or zig.

## parse

* struct / union / anonymous
* function pointer typedef
* function
  * mangling
  * pointer handling
  * const reference
  * default argument

* python generator
  * ctypes struct
  * add method to ctypes struct
  * pyi type annotation

* zig generator
  * method call
  * variadic argument

## clang.cindex

This library is use 'clang.cindex` from <https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-13.0.0/clang/bindings/python/clang/>.
And placement in rawtypes.clang.

```py
from rawtypes.clang import cindex
```

## generated

* <https://github.com/ousttrue/pydear> is generated extension. Included [imgui](https://github.com/ocornut/imgui) and [picovg](https://github.com/ousttrue/picovg)
