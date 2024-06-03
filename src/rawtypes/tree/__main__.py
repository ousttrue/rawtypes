from typing import NamedTuple, cast, Iterator
import pathlib
import sys
import logging
from PySide6 import QtWidgets, QtCore, QtGui
from .. import cindex_util
from ..clang import cindex
from .flowlayout import FlowLayout
import collections


LOGGER = logging.getLogger(__name__)


class CursorNode(NamedTuple):
    cursor: cindex.Cursor
    children: list["CursorNode"]
    parent: "CursorNode|None"

    def traverse(self) -> Iterator["CursorNode"]:
        yield self
        for child in self.children:
            for x in child.traverse():
                yield x


class CIndexCursorModel(QtCore.QAbstractItemModel):
    def __init__(
        self, header: pathlib.Path, include_dirs: list[pathlib.Path] | None = None
    ):
        super().__init__()
        self.headers = ["spelling", "CursorKind"]

        self.tu = cindex_util.get_tu(header, include_dirs=include_dirs)
        self.header = header
        self.kind_map: dict[cindex.CursorKind, int] = collections.OrderedDict()
        self.root = self._traverse(self.tu.cursor)

        def in_header(node: CursorNode) -> bool:
            for x in node.traverse():
                if x.cursor.location.file:
                    if pathlib.Path(x.cursor.location.file.name) == self.header:
                        return True
            return False

        # only in header
        filtered = [child for child in self.root.children if in_header(child)]
        self.root.children.clear()
        self.root.children.extend(filtered)
        pass

    def _traverse(
        self,
        cursor: cindex.Cursor,
        parent: CursorNode | None = None,
        level: int = 0,
    ) -> CursorNode:
        self.kind_map[cursor.kind] = self.kind_map.get(cursor.kind, 0) + 1
        node = CursorNode(cursor, [], parent)
        for child in cursor.get_children():
            child_node = self._traverse(child, node, level + 1)
            node.children.append(child_node)
        # print(f'{"  " * level}{cursor.displayname}')
        return node

    def columnCount(self, parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex) -> int:  # type: ignore
        return len(self.headers)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: QtCore.Qt.ItemDataRole) -> str | None:  # type: ignore
        match orientation, role:
            case QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole:  # type: ignore
                return self.headers[section]
            case _:
                pass

    def data(self, index: QtCore.QModelIndex | QtCore.QPersistentModelIndex, role: QtCore.Qt.ItemDataRole) -> str | None:  # type: ignore
        if index.isValid():
            node = cast(CursorNode, index.internalPointer())  # type: ignore
            if role == QtCore.Qt.DisplayRole:  # type: ignore
                match index.column():
                    case 0:
                        return node.cursor.spelling
                    case 1:
                        return node.cursor.kind.name
                    case _:
                        raise RuntimeError()

    def rowCount(self, parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex) -> int:  # type: ignore
        if parent.isValid():
            parent_node = cast(CursorNode, parent.internalPointer())
            return len(parent_node.children)
        else:
            return 1

    def index(  # type: ignore
        self,
        row: int,
        column: int,
        parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> QtCore.QModelIndex:
        if parent.isValid():
            parent_node = cast(CursorNode, parent.internalPointer())
            child_node = parent_node.children[row]
            return self.createIndex(row, column, child_node)
        else:
            return self.createIndex(row, column, self.root)

    def parent(  # type: ignore
        self,
        child: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> QtCore.QModelIndex:
        if child.isValid():
            child_node = cast(CursorNode, child.internalPointer())
            if child_node.parent:
                row = child_node.parent.children.index(child_node)
                return self.createIndex(row, 0, child_node.parent)
            else:
                return QtCore.QModelIndex()
        else:
            return self.createIndex(0, 0, self.root)


class Filter(QtWidgets.QWidget):
    kind_changed = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.checkes: list[QtWidgets.QCheckBox] = []

    def set_kinds(self, kinds: dict[cindex.CursorKind, int]) -> None:
        self.checkes.clear()
        self.kinds = FlowLayout()
        for k, _ in kinds.items():
            checkbox = QtWidgets.QCheckBox(self)
            self.checkes.append(checkbox)
            checkbox.setText(k.name)  # type: ignore
            checkbox.setChecked(True)
            checkbox.checkStateChanged.connect(self.kind_changed)
            self.kinds.addWidget(checkbox)
        self.setLayout(self.kinds)

    def regex(self) -> str:
        tmp: list[str] = []
        for cb in self.checkes:
            if cb.isChecked():
                tmp.append(cb.text())
        return r"\(" + "|".join(tmp) + r"\)"


class Window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__(None)

        self.path: pathlib.Path = pathlib.Path()

        # menu
        self.menubar = self.menuBar()
        self.menubar.setNativeMenuBar(False)
        self.menu_file = self.menubar.addMenu("File")
        self.menu_file.addAction("Open", self._on_file_open)  # type: ignore
        self.menu_docks = self.menubar.addMenu("Docks")

        # status bar
        # self.sb = self.statusBar()
        # self.sb.showMessage("ステータスバー")

        # central
        self.text = QtWidgets.QTextEdit()
        font = QtGui.QFont("Monospace")
        font.setStyleHint(QtGui.QFont.StyleHint.TypeWriter)
        self.text.setCurrentFont(font)

        self.setCentralWidget(self.text)

        self.tree = QtWidgets.QTreeView()
        self._add_dock("tree", QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.tree)

        # # filter
        # self.proxy_model = QtCore.QSortFilterProxyModel()
        # self.tree.setModel(self.proxy_model)
        # self.filter = Filter()
        # self.filter.kind_changed.connect(self.on_filterChanged)
        # self._add_dock(
        #     "filter", QtCore.Qt.DockWidgetArea.TopDockWidgetArea, self.filter
        # )

    def _add_dock(
        self, name: str, area: QtCore.Qt.DockWidgetArea, widget: QtWidgets.QWidget
    ) -> QtWidgets.QDockWidget:
        dock = QtWidgets.QDockWidget(name, self)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        self.menu_docks.addAction(dock.toggleViewAction())  # type: ignore
        return dock

    def _on_file_open(self) -> None:
        file, ok = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open file", filter="header (*.h)"
        )
        if not ok:
            return

        self.open_header(pathlib.Path(file))

    # def on_filterChanged(self):
    #     self.proxy_model.setFilterKeyColumn(1)
    #     filter_regex = self.filter.regex()
    #     LOGGER.info(filter_regex)
    #     self.proxy_model.setFilterRegularExpression(filter_regex)

    def open_header(
        self, header: pathlib.Path, include_dirs: list[pathlib.Path] | None = None
    ) -> None:
        LOGGER.debug(header)
        self.path = header
        self.text.setText(header.read_text())
        # self.text.setReadOnly(True)

        model = CIndexCursorModel(header, include_dirs)
        self.tree.setModel(model)

        # self.filter.set_kinds(model.kind_map)
        # self.proxy_model.setSourceModel(model)
        # self.proxy_model.setDynamicSortFilter(True)

        self.tree.selectionModel().selectionChanged.connect(self.on_selected)

    def on_selected(self):
        indices = self.tree.selectionModel().selectedIndexes()
        if not indices:
            return

        node = cast(CursorNode, indices[0].internalPointer())
        loc = node.cursor.location
        if not loc.file:
            LOGGER.debug(f"not path")
            return

        if pathlib.Path(loc.file.name) != self.path:
            LOGGER.debug(f"not in :{self.path}")
            return

        LOGGER.info(loc)
        cursor = self.text.textCursor()
        b = cursor.document().findBlockByLineNumber(loc.line - 1)
        LOGGER.info(b.position())
        cursor.setPosition(
            b.position() + loc.column - 1,
            QtGui.QTextCursor.MoveMode.MoveAnchor,
        )
        self.text.setTextCursor(cursor)
        self.text.setFocus()


def main():
    logging.basicConfig(
        format="[%(levelname)s] %(filename)s:%(lineno)d => %(message)s",
        level=logging.DEBUG,
    )

    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.resize(1024, 768)
    window.show()

    header: pathlib.Path = cindex_util.CINDEX_HEADER
    window.open_header(header, [header.parent.parent])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
