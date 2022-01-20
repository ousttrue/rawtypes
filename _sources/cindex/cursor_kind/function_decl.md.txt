# FUNCTION_DECL

関数宣言。

```python
    def test_function(self):
        source = '''
float func(int a, const char *b = nullptr);
'''

        tu = pycindex.get_tu(
            'tmp.h', unsaved=[pycindex.Unsaved('tmp.h', source)])

        items = []

        def callback(*cursor_path: cindex.Cursor):
            cursor = cursor_path[-1]
            match cursor.location:
                case cindex.SourceLocation() as location:
                    if location.file:
                        # print([x.kind for x in cursor_path], location.file)
                        items.append(cursor_path)
            return True
        pycindex.traverse(tu, callback)
        for item in items:
            print(', '.join([str(c.kind) for c in item]))

        self.assertEqual(5, len(items))
        self.assertEqual('func', items[0][-1].spelling)
        self.assertEqual(cindex.TypeKind.FLOAT, items[0][-1].result_type.kind)
        self.assertEqual('a', items[1][-1].spelling)
        self.assertEqual(cindex.TypeKind.INT, items[1][-1].type.kind)
        self.assertEqual('b', items[2][-1].spelling)
        self.assertTrue(items[2][-1].type.is_const_qualified)
        self.assertEqual(cindex.TypeKind.POINTER, items[2][-1].type.kind)
```

```
CursorKind.FUNCTION_DECL
CursorKind.FUNCTION_DECL, CursorKind.PARM_DECL
CursorKind.FUNCTION_DECL, CursorKind.PARM_DECL
CursorKind.FUNCTION_DECL, CursorKind.PARM_DECL, CursorKind.UNEXPOSED_EXPR
CursorKind.FUNCTION_DECL, CursorKind.PARM_DECL, CursorKind.UNEXPOSED_EXPR, CursorKind.CXX_NULL_PTR_LITERAL_EXPR
```

## 名前

`items[0][-1].spelling`

### mangling 名

`items[0][-1].mangled_name`

## 返り値

`self.assertEqual(cindex.TypeKind.FLOAT, items[0][-1].result_type.kind)`

## 引数

### 0

```
self.assertEqual('a', items[1][-1].spelling)
self.assertEqual(cindex.TypeKind.INT, items[1][-1].type.kind)
```

### 1

```
self.assertEqual('b', items[2][-1].spelling)
self.assertTrue(items[2][-1].type.is_const_qualified)
self.assertEqual(cindex.TypeKind.POINTER, items[2][-1].type.kind)
```

### デフォルト引数

```
CursorKind.FUNCTION_DECL, CursorKind.PARM_DECL, CursorKind.UNEXPOSED_EXPR, CursorKind.CXX_NULL_PTR_LITERAL_EXPR
```
