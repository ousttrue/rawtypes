# rawtypes

A code generator using libclang for a python extension or zig.

## parse

* function
* pointer handling
* struct / union / anonymous
* typedef
* functin pointer
* const
* reference
* mangling
* method call
* default argument

* python generator
  * ctypes struct
  * add method to ctypes struct
  * pyi type annotation

* zig generator

## clang.cindex

This library is use 'clang.cindex` from <https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-13.0.0/clang/bindings/python/clang/>.
And placement in rawtypes.clang.

```py
from rawtypes.clang import cindex
```

## generated

* <https://github.com/ousttrue/pydear> is generated extension. Included [imgui](https://github.com/ocornut/imgui) and [picovg](https://github.com/ousttrue/picovg)
