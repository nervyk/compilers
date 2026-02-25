import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTextEdit,
    QSplitter,
    QToolBar,
    QStyle,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None

        self.editor = QTextEdit()
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Результаты анализа будут отображаться здесь")

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.output)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        self.init_actions()
        self.init_menu()
        self.init_toolbar()

        self.statusBar().showMessage("Готово")
        self.editor.document().modificationChanged.connect(self.update_title)
        self.update_title()
        self.resize(900, 600)

    def init_actions(self):
        style = self.style()

        self.act_new = QAction(style.standardIcon(QStyle.SP_FileIcon), "Новый", self)
        self.act_open = QAction(style.standardIcon(QStyle.SP_DialogOpenButton), "Открыть...", self)
        self.act_save = QAction(style.standardIcon(QStyle.SP_DialogSaveButton), "Сохранить", self)
        self.act_save_as = QAction("Сохранить как...", self)
        self.act_exit = QAction("Выход", self)

        self.act_undo = QAction("Отменить", self)
        self.act_redo = QAction("Повторить", self)
        self.act_cut = QAction("Вырезать", self)
        self.act_copy = QAction("Копировать", self)
        self.act_paste = QAction("Вставить", self)
        self.act_delete = QAction("Удалить", self)
        self.act_select_all = QAction("Выделить все", self)

        self.act_help = QAction("Справка", self)
        self.act_about = QAction("О программе", self)

        self.act_editor_font_inc = QAction("Шрифт редактора +", self)
        self.act_editor_font_dec = QAction("Шрифт редактора -", self)
        self.act_output_font_inc = QAction("Шрифт вывода +", self)
        self.act_output_font_dec = QAction("Шрифт вывода -", self)

        self.act_new.setShortcut(QKeySequence.New)
        self.act_open.setShortcut(QKeySequence.Open)
        self.act_save.setShortcut(QKeySequence.Save)
        self.act_save_as.setShortcut(QKeySequence.SaveAs)
        self.act_exit.setShortcut(QKeySequence.Quit)

        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_redo.setShortcut(QKeySequence.Redo)
        self.act_cut.setShortcut(QKeySequence.Cut)
        self.act_copy.setShortcut(QKeySequence.Copy)
        self.act_paste.setShortcut(QKeySequence.Paste)
        self.act_delete.setShortcut(QKeySequence.Delete)
        self.act_select_all.setShortcut(QKeySequence.SelectAll)
        self.act_editor_font_inc.setShortcut(QKeySequence("Ctrl+="))
        self.act_editor_font_dec.setShortcut(QKeySequence("Ctrl+-"))
        self.act_output_font_inc.setShortcut(QKeySequence("Ctrl+Shift+="))
        self.act_output_font_dec.setShortcut(QKeySequence("Ctrl+Shift+-"))

        self.act_new.triggered.connect(self.file_new)
        self.act_open.triggered.connect(self.file_open)
        self.act_save.triggered.connect(self.file_save)
        self.act_save_as.triggered.connect(self.file_save_as)
        self.act_exit.triggered.connect(self.close)

        self.act_undo.triggered.connect(self.editor.undo)
        self.act_redo.triggered.connect(self.editor.redo)
        self.act_cut.triggered.connect(self.editor.cut)
        self.act_copy.triggered.connect(self.editor.copy)
        self.act_paste.triggered.connect(self.editor.paste)
        self.act_delete.triggered.connect(self.edit_delete)
        self.act_select_all.triggered.connect(self.editor.selectAll)

        self.act_help.triggered.connect(self.show_help)
        self.act_about.triggered.connect(self.show_about)
        self.act_editor_font_inc.triggered.connect(lambda: self.change_font_size(self.editor, 1))
        self.act_editor_font_dec.triggered.connect(lambda: self.change_font_size(self.editor, -1))
        self.act_output_font_inc.triggered.connect(lambda: self.change_font_size(self.output, 1))
        self.act_output_font_dec.triggered.connect(lambda: self.change_font_size(self.output, -1))

    def init_menu(self):
        menu_file = self.menuBar().addMenu("Файл")
        menu_file.addAction(self.act_new)
        menu_file.addAction(self.act_open)
        menu_file.addAction(self.act_save)
        menu_file.addAction(self.act_save_as)
        menu_file.addSeparator()
        menu_file.addAction(self.act_exit)

        menu_edit = self.menuBar().addMenu("Правка")
        menu_edit.addAction(self.act_undo)
        menu_edit.addAction(self.act_redo)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_cut)
        menu_edit.addAction(self.act_copy)
        menu_edit.addAction(self.act_paste)
        menu_edit.addAction(self.act_delete)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_select_all)

        menu_help = self.menuBar().addMenu("Справка")
        menu_help.addAction(self.act_help)
        menu_help.addAction(self.act_about)

        menu_view = self.menuBar().addMenu("Вид")
        menu_view.addAction(self.act_editor_font_inc)
        menu_view.addAction(self.act_editor_font_dec)
        menu_view.addSeparator()
        menu_view.addAction(self.act_output_font_inc)
        menu_view.addAction(self.act_output_font_dec)

    def init_toolbar(self):
        toolbar = QToolBar("Инструменты")
        toolbar.setMovable(True)
        self.addToolBar(toolbar)

        toolbar.addAction(self.act_new)
        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)
        toolbar.addAction(self.act_save_as)
        toolbar.addSeparator()
        toolbar.addAction(self.act_undo)
        toolbar.addAction(self.act_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.act_cut)
        toolbar.addAction(self.act_copy)
        toolbar.addAction(self.act_paste)
        toolbar.addAction(self.act_delete)
        toolbar.addAction(self.act_select_all)
        toolbar.addSeparator()
        toolbar.addAction(self.act_help)
        toolbar.addAction(self.act_about)
        toolbar.addSeparator()
        toolbar.addAction(self.act_exit)

    def maybe_save(self):
        if not self.editor.document().isModified():
            return True
        msg = QMessageBox(self)
        msg.setWindowTitle("Несохраненные изменения")
        msg.setText("Сохранить изменения?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Yes)
        res = msg.exec()
        if res == QMessageBox.Yes:
            return self.file_save()
        if res == QMessageBox.No:
            return True
        return False

    def file_new(self):
        if not self.maybe_save():
            return
        self.editor.clear()
        self.editor.document().setModified(False)
        self.current_file = None
        self.update_title()

    def file_open(self):
        if not self.maybe_save():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Текстовые файлы (*.txt);;Все файлы (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")
            return
        self.editor.setPlainText(data)
        self.editor.document().setModified(False)
        self.current_file = path
        self.update_title()

    def file_save(self):
        if not self.current_file:
            return self.file_save_as()
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")
            return False
        self.editor.document().setModified(False)
        self.update_title()
        return True

    def file_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить как", "", "Текстовые файлы (*.txt);;Все файлы (*)")
        if not path:
            return False
        self.current_file = path
        return self.file_save()

    def edit_delete(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
        else:
            cursor.deleteChar()

    def change_font_size(self, widget, delta):
        font = QFont(widget.font())
        size = font.pointSize()
        if size <= 0:
            size = 10
        size = max(8, min(32, size + delta))
        font.setPointSize(size)
        widget.setFont(font)
        self.statusBar().showMessage(f"Размер шрифта: {size}", 1500)

    def show_help(self):
        text = (
            "Файл: создать, открыть, сохранить, сохранить как, выход.\n"
            "Правка: отмена/повтор, вырезать/копировать/вставить, удалить, выделить все.\n"
            "Справка: описание функций и окно о программе."
        )
        QMessageBox.information(self, "Справка", text)

    def show_about(self):
        QMessageBox.information(self, "О программе", "GUI для языкового процессора. Лабораторная работа 1.")

    def update_title(self):
        name = self.current_file if self.current_file else "Безымянный"
        mod = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"Редактор {name}{mod}")
        self.statusBar().showMessage(name)

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
