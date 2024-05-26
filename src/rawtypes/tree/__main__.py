from typing import NamedTuple, cast
import pathlib
import sys
import logging
from PySide6 import QtWidgets, QtCore, QtGui
from .. import cindex_util
from rawtypes.clang15 import cindex

LOGGER = logging.getLogger(__name__)


class CursorNode(NamedTuple):
    cursor: cindex.Cursor
    children: list["CursorNode"]
    parent: "CursorNode|None"


class CIndexCursorModel(QtCore.QAbstractTableModel):
    def __init__(self, tu: cindex.TranslationUnit):
        super().__init__()
        self.headers = ["displayname", "kind"]
        self.tu = tu
        self.root = self._traverse(tu.cursor)

    def _traverse(
        self, cursor: cindex.Cursor, parent: CursorNode | None = None
    ) -> CursorNode:
        node = CursorNode(cursor, [], parent)
        for child in cursor.get_children():
            child_node = self._traverse(child, node)
            node.children.append(child_node)
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
                        return node.cursor.displayname
                    case 1:
                        return str(node.cursor.kind)
                    case _:
                        raise RuntimeError()

    def rowCount(self, parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex) -> int:  # type: ignore
        if parent.isValid():
            parent_node = cast(CursorNode, parent.internalPointer())
        else:
            parent_node = self.root
        return len(parent_node.children)

    def index(  # type: ignore
        self,
        row: int,
        column: int,
        parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> QtCore.QModelIndex:
        if parent.isValid():
            parent_node = cast(CursorNode, parent.internalPointer())
        else:
            parent_node = self.root
        child_node = parent_node.children[row]
        return self.createIndex(row, column, child_node)

    def parent(  # type: ignore
        self,
        child: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> QtCore.QModelIndex:
        if child.isValid():
            child_node = cast(CursorNode, child.internalPointer())
            if child_node.parent:
                return self.createIndex(0, 0, child_node.parent)

        return QtCore.QModelIndex()


class Window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__(None)

        # menu
        self.menubar = self.menuBar()
        self.menubar.setNativeMenuBar(False)
        self.menu_docks = self.menubar.addMenu("Docks")
        # status bar
        self.sb = self.statusBar()
        self.sb.showMessage("ステータスバー")

        # central
        self.tree = QtWidgets.QTreeView()
        self.setCentralWidget(self.tree)
        self.proxy_model = QtCore.QSortFilterProxyModel()
        self.tree.setModel(self.proxy_model)

        # filter
        self.filter = QtWidgets.QLineEdit(self)
        self.filter.textChanged.connect(self.on_filterChanged)
        self.filter_dock = QtWidgets.QDockWidget("filter", self)
        self.filter_dock.setWidget(self.filter)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.TopDockWidgetArea, self.filter_dock)
        self.menu_docks.addAction(self.filter_dock.toggleViewAction())  # type: ignore

    def on_filterChanged(self):
        self.proxy_model.setFilterKeyColumn(1)
        self.proxy_model.setFilterFixedString(self.filter.text())

    def open_header(self, header: pathlib.Path) -> None:
        LOGGER.debug(header)
        tu = cindex_util.get_tu(header)

        model = CIndexCursorModel(tu)
        self.proxy_model.setSourceModel(model)
        self.proxy_model.setDynamicSortFilter(True)


def main(header: pathlib.Path = cindex_util.CINDEX_HEADER):
    logging.basicConfig(
        format="[%(levelname)s] %(filename)s:%(lineno)d => %(message)s",
        level=logging.DEBUG,
    )

    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.resize(1024, 768)
    window.show()
    window.open_header(header)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
