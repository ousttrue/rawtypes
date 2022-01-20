# ImGui

## 対象を "imgui.h" 内の関数に絞る

```python
    tu = get_tu(args.entrypoint)

    # traverse
    functions = []

    def filter_imgui(*cursor_path: cindex.Cursor):
        cursor = cursor_path[-1]
        location: cindex.SourceLocation = cursor.location
        if not location:
            return
        if not location.file:
            return

        if location.file.name == args.entrypoint:
            if cursor.kind == cindex.CursorKind.FUNCTION_DECL:
                functions.append(cursor_path)

        return True
    traverse(tu, filter_imgui)
```

関数が 400 個くらい取れた。

```
0: CursorKind.NAMESPACE, CursorKind.FUNCTION_DECL: CreateContext
1: CursorKind.NAMESPACE, CursorKind.FUNCTION_DECL: DestroyContext
2: CursorKind.NAMESPACE, CursorKind.FUNCTION_DECL: GetCurrentContext
3: CursorKind.NAMESPACE, CursorKind.FUNCTION_DECL: SetCurrentContext
4: CursorKind.NAMESPACE, CursorKind.FUNCTION_DECL: GetIO

409: CursorKind.NAMESPACE, CursorKind.FUNCTION_DECL: BeginPopupContextWindow
410: CursorKind.NAMESPACE, CursorKind.FUNCTION_DECL: TreeAdvanceToLabelPos
411: CursorKind.NAMESPACE, CursorKind.FUNCTION_DECL: SetNextTreeNodeOpen
412: CursorKind.NAMESPACE, CursorKind.FUNCTION_DECL: GetContentRegionAvailWidth
```
