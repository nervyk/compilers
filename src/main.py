import sys
import re
from PySide6.QtCore import Qt, QRegularExpression, QSize
from PySide6.QtGui import QAction, QKeySequence, QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTextEdit,
    QSplitter,
    QToolBar,
    QStyle,
    QVBoxLayout,
)


class BasicHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        kw = QTextCharFormat()
        kw.setForeground(QColor("#0b57d0"))
        kw.setFontWeight(QFont.Bold)
        keywords = [
            "if", "else", "for", "while", "return", "break", "continue", "def", "class",
            "import", "from", "try", "except", "finally", "with", "as", "pass",
            "int", "float", "char", "double", "void", "struct", "const", "static",
            "public", "private", "protected", "switch", "case", "default",
        ]
        for word in keywords:
            self.rules.append((QRegularExpression(rf"\b{word}\b"), kw))

        num = QTextCharFormat()
        num.setForeground(QColor("#b00020"))
        self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), num))

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor("#137333"))
        self.rules.append((QRegularExpression(r'"[^"\n]*"'), string_fmt))
        self.rules.append((QRegularExpression(r"'[^'\n]*'"), string_fmt))

        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#6a737d"))
        self.rules.append((QRegularExpression(r"#.*$"), comment_fmt))
        self.rules.append((QRegularExpression(r"//.*$"), comment_fmt))

    def highlightBlock(self, text):
        for pattern, text_format in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), text_format)


class TextInfoDialog(QDialog):
    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(text)
        layout.addWidget(viewer)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.setAcceptDrops(True)
        self.text_topics = {
            "Постановка задачи": (
                "Разработать графическое приложение в виде текстового редактора.\n\n"
                "Приложение должно содержать меню, панель инструментов, область редактирования "
                "и область вывода результатов работы языкового процессора.\n\n"
                "Реализация должна быть кроссплатформенной и подготовленной к дальнейшему "
                "расширению функционала."
            ),
            "Грамматика": (
                "Пример упрощенной грамматики выражений:\n\n"
                "<expr> -> <term> ((+|-) <term>)*\n"
                "<term> -> <factor> ((*|/) <factor>)*\n"
                "<factor> -> id | number | '(' <expr> ')'\n\n"
                "Эта информация используется как справочный раздел меню 'Текст'."
            ),
            "Классификация грамматики": (
                "Для лабораторной работы используется контекстно-свободная грамматика.\n\n"
                "В дальнейшем раздел может быть расширен описанием классификации по Хомскому, "
                "свойств грамматики и ограничений выбранного метода анализа."
            ),
            "Метод анализа": (
                "На текущем этапе реализован базовый демонстрационный анализ текста.\n\n"
                "Дальнейшее расширение: лексический и синтаксический анализ входного текста "
                "с выводом сообщений в нижнюю область результатов."
            ),
            "Тестовый пример": (
                "int a = 10;\n"
                "float b = 2.5;\n"
                "if (a > 0) {\n"
                "    b = b + a;\n"
                "}\n"
            ),
            "Список литературы": (
                "1. Ахо А., Сети Р., Ульман Д. Компиляторы: принципы, технологии и инструменты.\n"
                "2. Вирт Н. Построение компиляторов.\n"
                "3. Документация Qt / PySide6."
            ),
        }

        self.editor = QTextEdit()
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Результаты анализа будут отображаться здесь")
        self.highlighter = BasicHighlighter(self.editor.document())

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.output)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        self.init_actions()
        self.init_menu()
        self.init_toolbars()

        self.statusBar().showMessage("Готово")
        self.editor.document().modificationChanged.connect(self.update_title)
        self.update_title()
        self.resize(900, 600)

    def init_actions(self):
        style = self.style()

        def pick_icon(theme_names, fallback):
            for name in theme_names:
                icon = QIcon.fromTheme(name)
                if not icon.isNull():
                    return icon
            return fallback

        self.act_new = QAction(
            pick_icon(["document-new"], style.standardIcon(QStyle.SP_FileIcon)),
            "Новый",
            self,
        )
        self.act_open = QAction(
            pick_icon(["document-open", "folder-open"], style.standardIcon(QStyle.SP_DialogOpenButton)),
            "Открыть...",
            self,
        )
        self.act_save = QAction(
            pick_icon(["document-save"], style.standardIcon(QStyle.SP_DialogSaveButton)),
            "Сохранить",
            self,
        )
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
        self.act_run = QAction(
            pick_icon(["media-playback-start", "system-run"], style.standardIcon(QStyle.SP_MediaPlay)),
            "Пуск",
            self,
        )
        self.act_text_task = QAction("Постановка задачи", self)
        self.act_text_grammar = QAction("Грамматика", self)
        self.act_text_classification = QAction("Классификация грамматики", self)
        self.act_text_method = QAction("Метод анализа", self)
        self.act_text_example = QAction("Тестовый пример", self)
        self.act_text_literature = QAction("Список литературы", self)
        self.act_text_source = QAction("Исходный код программы", self)

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
        self.act_run.setShortcut(QKeySequence("F5"))
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
        self.act_run.triggered.connect(self.run_analysis)
        self.act_text_task.triggered.connect(lambda: self.show_text_topic("Постановка задачи"))
        self.act_text_grammar.triggered.connect(lambda: self.show_text_topic("Грамматика"))
        self.act_text_classification.triggered.connect(lambda: self.show_text_topic("Классификация грамматики"))
        self.act_text_method.triggered.connect(lambda: self.show_text_topic("Метод анализа"))
        self.act_text_example.triggered.connect(lambda: self.show_text_topic("Тестовый пример"))
        self.act_text_literature.triggered.connect(lambda: self.show_text_topic("Список литературы"))
        self.act_text_source.triggered.connect(self.show_source_code)
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

        menu_text = self.menuBar().addMenu("Текст")
        menu_text.addAction(self.act_text_task)
        menu_text.addAction(self.act_text_grammar)
        menu_text.addAction(self.act_text_classification)
        menu_text.addAction(self.act_text_method)
        menu_text.addAction(self.act_text_example)
        menu_text.addAction(self.act_text_literature)
        menu_text.addSeparator()
        menu_text.addAction(self.act_text_source)

        self.menuBar().addAction(self.act_run)

        menu_help = self.menuBar().addMenu("Справка")
        menu_help.addAction(self.act_help)
        menu_help.addAction(self.act_about)

        menu_view = self.menuBar().addMenu("Вид")
        menu_view.addAction(self.act_editor_font_inc)
        menu_view.addAction(self.act_editor_font_dec)
        menu_view.addSeparator()
        menu_view.addAction(self.act_output_font_inc)
        menu_view.addAction(self.act_output_font_dec)

    def init_toolbars(self):
        toolbar_icons = QToolBar("Быстрые команды")
        toolbar_icons.setMovable(True)
        toolbar_icons.setToolButtonStyle(Qt.ToolButtonIconOnly)
        toolbar_icons.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar_icons)

        toolbar_icons.addAction(self.act_new)
        toolbar_icons.addAction(self.act_open)
        toolbar_icons.addAction(self.act_save)
        toolbar_icons.addAction(self.act_run)

        self.addToolBarBreak()

        toolbar_text = QToolBar("Инструменты")
        toolbar_text.setMovable(True)
        toolbar_text.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(toolbar_text)

        toolbar_text.addAction(self.act_save_as)
        toolbar_text.addAction(self.act_exit)
        toolbar_text.addSeparator()
        toolbar_text.addAction(self.act_undo)
        toolbar_text.addAction(self.act_redo)
        toolbar_text.addSeparator()
        toolbar_text.addAction(self.act_cut)
        toolbar_text.addAction(self.act_copy)
        toolbar_text.addAction(self.act_paste)
        toolbar_text.addAction(self.act_delete)
        toolbar_text.addAction(self.act_select_all)
        toolbar_text.addSeparator()
        toolbar_text.addAction(self.act_editor_font_inc)
        toolbar_text.addAction(self.act_editor_font_dec)
        toolbar_text.addAction(self.act_output_font_inc)
        toolbar_text.addAction(self.act_output_font_dec)
        toolbar_text.addSeparator()
        toolbar_text.addAction(self.act_help)
        toolbar_text.addAction(self.act_about)

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
        self.load_file(path)

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

    def load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")
            return False
        self.editor.setPlainText(data)
        self.editor.document().setModified(False)
        self.current_file = path
        self.update_title()
        self.statusBar().showMessage(f"Открыт файл: {path}", 2000)
        return True

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

    def show_text_topic(self, title):
        dialog = TextInfoDialog(title, self.text_topics.get(title, ""), self)
        dialog.exec()

    def show_source_code(self):
        try:
            with open(__file__, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть исходный код:\n{e}")
            return
        dialog = TextInfoDialog("Исходный код программы", text, self)
        dialog.exec()

    def run_analysis(self):
        text = self.editor.toPlainText()
        if not text.strip():
            self.output.setPlainText("Пустой текст. Нечего анализировать.")
            self.statusBar().showMessage("Пуск: пустой текст", 2000)
            return

        lines = text.splitlines()
        if not lines:
            lines = [text]

        errors = []
        stack = []
        pairs = {")": "(", "]": "[", "}": "{"}
        opens = set(pairs.values())
        keyword_set = {
            "if", "else", "for", "while", "return", "break", "continue", "def", "class",
            "import", "from", "try", "except", "finally", "with", "as", "pass",
            "int", "float", "char", "double", "void", "struct", "const", "static",
            "public", "private", "protected", "switch", "case", "default",
        }

        for line_no, line in enumerate(lines, start=1):
            for col_no, ch in enumerate(line, start=1):
                if ch in opens:
                    stack.append((ch, line_no, col_no))
                elif ch in pairs:
                    if not stack or stack[-1][0] != pairs[ch]:
                        errors.append((line_no, col_no, f"Несогласованная скобка '{ch}'"))
                    else:
                        stack.pop()
                elif ch == "@":
                    errors.append((line_no, col_no, "Недопустимый символ '@'"))

            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            if stripped.endswith((";", "{", "}", ":")):
                continue
            if re.match(r"^(if|for|while|switch)\s*\(.*\)$", stripped):
                continue
            if stripped in {"else", "do"}:
                continue
            if stripped.startswith("else "):
                continue
            if "=" in stripped or re.search(r"\b(return|break|continue)\b", stripped):
                errors.append((line_no, max(len(line), 1), "Возможен пропуск ';'"))

        for ch, line_no, col_no in reversed(stack):
            errors.append((line_no, col_no, f"Нет закрывающей скобки для '{ch}'"))

        words = re.findall(r"[A-Za-z_][A-Za-z_0-9]*", text)
        numbers = re.findall(r"\b\d+(\.\d+)?\b", text)
        keywords_found = sum(1 for w in words if w in keyword_set)

        result_lines = [
            "Результаты анализа",
            f"Строк: {len(lines)}",
            f"Символов: {len(text)}",
            f"Идентификаторов/слов: {len(words)}",
            f"Чисел: {len(numbers)}",
            f"Ключевых слов: {keywords_found}",
            "",
        ]

        if errors:
            result_lines.append("Ошибки:")
            for line_no, col_no, msg in errors:
                result_lines.append(f"L{line_no}:C{col_no} {msg}")
        else:
            result_lines.append("Ошибок не найдено.")

        self.output.setPlainText("\n".join(result_lines))
        self.statusBar().showMessage("Анализ завершен", 2000)

    def show_help(self):
        text = (
            "Файл: создать, открыть, сохранить, сохранить как, выход.\n"
            "Правка: отмена/повтор, вырезать/копировать/вставить, удалить, выделить все.\n"
            "Текст: учебные материалы и исходный код программы.\n"
            "Пуск: базовый анализ текста (F5), вывод результата в нижнюю область.\n"
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

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        urls = [url for url in event.mimeData().urls() if url.isLocalFile()]
        if not urls:
            event.ignore()
            return
        if not self.maybe_save():
            event.ignore()
            return
        path = urls[0].toLocalFile()
        if self.load_file(path):
            event.acceptProposedAction()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
