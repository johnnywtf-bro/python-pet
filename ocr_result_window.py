# ocr_result_window.py
from PyQt5 import QtCore, QtGui, QtWidgets

class OcrResultWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📄 截圖文字辨識結果")
        self.resize(680, 520)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        self.search_box = QtWidgets.QLineEdit(self)
        self.search_box.setPlaceholderText("搜尋（Enter 下一個 / Shift+Enter 上一個）")
        self.text_edit = QtWidgets.QPlainTextEdit(self)
        self.text_edit.setReadOnly(False)
        self.text_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)

        self.status = QtWidgets.QLabel("—")
        status_bar = QtWidgets.QStatusBar(self)
        status_bar.addPermanentWidget(self.status)

        btn_copy = QtWidgets.QPushButton("複製(Ctrl+C)")
        btn_save = QtWidgets.QPushButton("另存文字(Ctrl+S)")
        btn_wrap = QtWidgets.QPushButton("切換自動換行")
        btn_wrap.setCheckable(True); btn_wrap.setChecked(True)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.search_box)
        top.addWidget(btn_copy)
        top.addWidget(btn_save)
        top.addWidget(btn_wrap)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.text_edit)
        lay.addWidget(status_bar)

        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+C"), self, activated=self.copy_all)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=self.save_text)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+F"), self, activated=lambda: self.search_box.setFocus())

        btn_copy.clicked.connect(self.copy_all)
        btn_save.clicked.connect(self.save_text)
        btn_wrap.toggled.connect(self.toggle_wrap)
        self.search_box.returnPressed.connect(self.find_next)
        self.search_box.installEventFilter(self)

        self.text_edit.textChanged.connect(self._update_status)

    def set_text(self, text: str):
        self.text_edit.setPlainText(text or "")
        self.text_edit.moveCursor(QtGui.QTextCursor.Start)
        self._update_status()

    def copy_all(self):
        self.text_edit.selectAll()
        self.text_edit.copy()
        self.status.setText("已複製全部內容")

    def save_text(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "另存為文字檔", "ocr_result.txt", "Text Files (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text_edit.toPlainText())
            self.status.setText(f"已儲存：{path}")

    def toggle_wrap(self, on: bool):
        mode = QtWidgets.QPlainTextEdit.WidgetWidth if on else QtWidgets.QPlainTextEdit.NoWrap
        self.text_edit.setLineWrapMode(mode)

    def find_next(self):
        key = self.search_box.text()
        if not key: return
        flags = QtGui.QTextDocument.FindFlags()
        if QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier:
            flags |= QtGui.QTextDocument.FindBackward
        if not self.text_edit.find(key, flags):
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start if not (flags & QtGui.QTextDocument.FindBackward)
                                else QtGui.QTextCursor.End)
            self.text_edit.setTextCursor(cursor)
            self.text_edit.find(key, flags)

    def eventFilter(self, obj, ev):
        if obj is self.search_box and ev.type() == QtCore.QEvent.KeyPress and ev.key() == QtCore.Qt.Key_Return:
            self.find_next(); return True
        return super().eventFilter(obj, ev)

    def _update_status(self):
        text = self.text_edit.toPlainText()
        lines = text.count("\n") + (1 if text else 0)
        chars = len(text)
        self.status.setText(f"行數：{lines}　字元：{chars}")
