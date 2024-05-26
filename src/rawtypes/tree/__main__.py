import pathlib
import sys
import logging
from PySide6 import QtWidgets
from .. import cindex_util


LOGGER = logging.getLogger(__name__)


class Window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__(None)

        # menu
        self.menubar = self.menuBar()
        self.menubar.setNativeMenuBar(False)


def main(header: pathlib.Path = cindex_util.CINDEX_HEADER):
    logging.basicConfig(
        format="[%(levelname)s] %(filename)s:%(lineno)d => %(message)s",
        level=logging.DEBUG,
    )

    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.resize(1024, 768)
    window.show()
    # window.open_file(path)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
