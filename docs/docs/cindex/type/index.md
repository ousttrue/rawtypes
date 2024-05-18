# CXType: 型の処理

* FUNCTION_DECL の result_type
* PARM_DECL の type
* FIELD_DECL の type
* TYPEDEF_DECL の underlying_type

など。

## 基本型

`void`, `int`, `float` など。
Type.kind から直接わかる。

## CXType_Pointer / CXType_LValueReference 

基本型か型参照が出現するまで `get_pointee()` で参照を剥がす。

### const

参照を剥がした各階層で `is_const_qualified` する。
`const char *p` と `char *const p` の違い。

## CXType_ConstantArray

`get_array_element_type`
`get_array_size`

## CXType_DependentSizedArray, CXType_IncompleteArray

`get_array_element_type`

## CXType_FunctionProto

関数ポインタ。
`CXType_FunctionProto`

## CXType_Typedef 

## CXType_Enum 

## CXType_Elaborated 

## CXType_Record 
