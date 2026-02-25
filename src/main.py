import sys
import re
from pathlib import Path
from PySide6.QtCore import Qt, QRegularExpression, QSize, QRect
from PySide6.QtGui import (
    QAction,
    QKeySequence,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QColor,
    QIcon,
    QPainter,
    QTextFormat,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QTextEdit,
    QPlainTextEdit,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QStyle,
    QVBoxLayout,
    QWidget,
    QTabWidget,
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
            self.rules.append((QRegularExpression(rf"\\b{word}\\b"), kw))

        num = QTextCharFormat()
        num.setForeground(QColor("#b00020"))
        self.rules.append((QRegularExpression(r"\\b\\d+(\\.\\d+)?\\b"), num))

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor("#137333"))
        self.rules.append((QRegularExpression(r'"[^"\\n]*"'), string_fmt))
        self.rules.append((QRegularExpression(r"'[^'\\n]*'"), string_fmt))

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


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.file_path = None
        self.untitled_id = None
        self.highlighter = BasicHighlighter(self.document())
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#f1f3f4"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#5f6368"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            block_number += 1
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())

    def highlight_current_line(self):
        if self.isReadOnly():
            self.setExtraSelections([])
            return
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#eef4ff"))
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])


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
        self.setAcceptDrops(True)
        self.untitled_counter = 1
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

        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.setMovable(True)
        self.editor_tabs.tabCloseRequested.connect(self.close_editor_tab)
        self.editor_tabs.currentChanged.connect(self.on_editor_tab_changed)

        self.output_tabs = QTabWidget()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Результаты анализа будут отображаться здесь")
        self.output_errors = QTableWidget(0, 3)
        self.output_errors.setHorizontalHeaderLabels(["Строка", "Столбец", "Сообщение"])
        self.output_errors.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.output_errors.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.output_errors.setSelectionMode(QAbstractItemView.SingleSelection)
        self.output_errors.verticalHeader().setVisible(False)
        self.output_errors.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.output_errors.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.output_errors.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.output_tabs.addTab(self.output_text, "Результат")
        self.output_tabs.addTab(self.output_errors, "Ошибки")

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.editor_tabs)
        splitter.addWidget(self.output_tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self.init_actions()
        self.init_menu()
        self.init_toolbars()

        self.create_editor_tab(make_current=True)
        self.statusBar().showMessage("Готово")
        self.update_title()
        self.resize(900, 600)

    def pick_icon(self, theme_names, fallback):
        for name in theme_names:
            icon = QIcon.fromTheme(name)
            if not icon.isNull():
                return icon
        return fallback

    def init_actions(self):
        style = self.style()

        self.act_new = QAction(
            self.pick_icon(["document-new"], style.standardIcon(QStyle.SP_FileIcon)),
            "Новый",
            self,
        )
        self.act_open = QAction(
            self.pick_icon(["document-open", "folder-open"], style.standardIcon(QStyle.SP_DialogOpenButton)),
            "Открыть...",
            self,
        )
        self.act_save = QAction(
            self.pick_icon(["document-save"], style.standardIcon(QStyle.SP_DialogSaveButton)),
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
            self.pick_icon(["media-playback-start", "system-run"], style.standardIcon(QStyle.SP_MediaPlay)),
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

        self.act_undo.triggered.connect(self.edit_undo)
        self.act_redo.triggered.connect(self.edit_redo)
        self.act_cut.triggered.connect(self.edit_cut)
        self.act_copy.triggered.connect(self.edit_copy)
        self.act_paste.triggered.connect(self.edit_paste)
        self.act_delete.triggered.connect(self.edit_delete)
        self.act_select_all.triggered.connect(self.edit_select_all)

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
        self.act_editor_font_inc.triggered.connect(lambda: self.change_editor_font_size(1))
        self.act_editor_font_dec.triggered.connect(lambda: self.change_editor_font_size(-1))
        self.act_output_font_inc.triggered.connect(lambda: self.change_output_font_size(1))
        self.act_output_font_dec.triggered.connect(lambda: self.change_output_font_size(-1))

    def init_menu(self):
        self.menu_file = self.menuBar().addMenu("Файл")
        self.menu_file.addAction(self.act_new)
        self.menu_file.addAction(self.act_open)
        self.menu_file.addAction(self.act_save)
        self.menu_file.addAction(self.act_save_as)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_exit)

        self.menu_edit = self.menuBar().addMenu("Правка")
        self.menu_edit.addAction(self.act_undo)
        self.menu_edit.addAction(self.act_redo)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.act_cut)
        self.menu_edit.addAction(self.act_copy)
        self.menu_edit.addAction(self.act_paste)
        self.menu_edit.addAction(self.act_delete)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.act_select_all)

        self.menu_text = self.menuBar().addMenu("Текст")
        self.menu_text.addAction(self.act_text_task)
        self.menu_text.addAction(self.act_text_grammar)
        self.menu_text.addAction(self.act_text_classification)
        self.menu_text.addAction(self.act_text_method)
        self.menu_text.addAction(self.act_text_example)
        self.menu_text.addAction(self.act_text_literature)
        self.menu_text.addSeparator()
        self.menu_text.addAction(self.act_text_source)

        self.menuBar().addAction(self.act_run)

        self.menu_help = self.menuBar().addMenu("Справка")
        self.menu_help.addAction(self.act_help)
        self.menu_help.addAction(self.act_about)

        self.menu_view = self.menuBar().addMenu("Вид")
        self.menu_view.addAction(self.act_editor_font_inc)
        self.menu_view.addAction(self.act_editor_font_dec)
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.act_output_font_inc)
        self.menu_view.addAction(self.act_output_font_dec)

    def init_toolbars(self):
        self.toolbar_icons = QToolBar("Быстрые команды")
        self.toolbar_icons.setMovable(True)
        self.toolbar_icons.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolbar_icons.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar_icons)

        self.toolbar_icons.addAction(self.act_new)
        self.toolbar_icons.addAction(self.act_open)
        self.toolbar_icons.addAction(self.act_save)
        self.toolbar_icons.addAction(self.act_run)

        self.addToolBarBreak()

        self.toolbar_text = QToolBar("Инструменты")
        self.toolbar_text.setMovable(True)
        self.toolbar_text.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(self.toolbar_text)

        self.toolbar_text.addAction(self.act_save_as)
        self.toolbar_text.addAction(self.act_exit)
        self.toolbar_text.addSeparator()
        self.toolbar_text.addAction(self.act_undo)
        self.toolbar_text.addAction(self.act_redo)
        self.toolbar_text.addSeparator()
        self.toolbar_text.addAction(self.act_cut)
        self.toolbar_text.addAction(self.act_copy)
        self.toolbar_text.addAction(self.act_paste)
        self.toolbar_text.addAction(self.act_delete)
        self.toolbar_text.addAction(self.act_select_all)
        self.toolbar_text.addSeparator()
        self.toolbar_text.addAction(self.act_editor_font_inc)
        self.toolbar_text.addAction(self.act_editor_font_dec)
        self.toolbar_text.addAction(self.act_output_font_inc)
        self.toolbar_text.addAction(self.act_output_font_dec)
        self.toolbar_text.addSeparator()
        self.toolbar_text.addAction(self.act_help)
        self.toolbar_text.addAction(self.act_about)

    def create_editor_tab(self, text="", file_path=None, make_current=True):
        editor = CodeEditor()
        editor.setPlainText(text)
        editor.document().setModified(False)
        editor.file_path = file_path
        editor.untitled_id = self.untitled_counter
        self.untitled_counter += 1
        editor.document().modificationChanged.connect(lambda _=False, e=editor: self.on_editor_modified(e))
        editor.cursorPositionChanged.connect(self.update_cursor_status)
        if self.editor_tabs.count() > 0:
            current_font = self.current_editor().font()
            editor.setFont(current_font)
        index = self.editor_tabs.addTab(editor, "")
        self.update_editor_tab(index)
        if make_current:
            self.editor_tabs.setCurrentIndex(index)
        return editor

    def current_editor(self):
        widget = self.editor_tabs.currentWidget()
        if isinstance(widget, CodeEditor):
            return widget
        return None

    def current_file(self):
        editor = self.current_editor()
        if not editor:
            return None
        return editor.file_path

    def editor_display_name(self, editor):
        if editor.file_path:
            name = Path(editor.file_path).name
        else:
            name = f"Безымянный {editor.untitled_id}"
        if editor.document().isModified():
            name += "*"
        return name

    def update_editor_tab(self, index):
        editor = self.editor_tabs.widget(index)
        if not isinstance(editor, CodeEditor):
            return
        title = self.editor_display_name(editor)
        self.editor_tabs.setTabText(index, title)
        self.editor_tabs.setTabToolTip(index, editor.file_path or title)

    def on_editor_modified(self, editor):
        for i in range(self.editor_tabs.count()):
            if self.editor_tabs.widget(i) is editor:
                self.update_editor_tab(i)
                break
        if editor is self.current_editor():
            self.update_title()

    def on_editor_tab_changed(self, _index):
        self.update_title()
        self.update_cursor_status()

    def close_editor_tab(self, index):
        editor = self.editor_tabs.widget(index)
        if not isinstance(editor, CodeEditor):
            return
        if not self.maybe_save(editor):
            return
        self.editor_tabs.removeTab(index)
        editor.deleteLater()
        if self.editor_tabs.count() == 0:
            self.create_editor_tab(make_current=True)
        self.update_title()

    def maybe_save(self, editor=None):
        editor = editor or self.current_editor()
        if not editor or not editor.document().isModified():
            return True
        name = editor.file_path or f"Безымянный {editor.untitled_id}"
        msg = QMessageBox(self)
        msg.setWindowTitle("Несохраненные изменения")
        msg.setText(f"Сохранить изменения в файле '{name}'?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Yes)
        res = msg.exec()
        if res == QMessageBox.Yes:
            return self.file_save(editor=editor)
        if res == QMessageBox.No:
            return True
        return False

    def can_reuse_editor(self, editor):
        if not editor:
            return False
        if editor.file_path:
            return False
        if editor.document().isModified():
            return False
        return not editor.toPlainText()

    def find_open_editor_by_path(self, path):
        target = str(Path(path))
        for i in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(i)
            if isinstance(editor, CodeEditor) and editor.file_path and str(Path(editor.file_path)) == target:
                return i, editor
        return -1, None

    def file_new(self):
        self.create_editor_tab(make_current=True)

    def file_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Текстовые файлы (*.txt);;Все файлы (*)")
        if not path:
            return
        self.open_path(path)

    def open_path(self, path):
        index, editor = self.find_open_editor_by_path(path)
        if editor:
            self.editor_tabs.setCurrentIndex(index)
            self.statusBar().showMessage(f"Файл уже открыт: {path}", 2000)
            return True

        editor = self.current_editor()
        if not self.can_reuse_editor(editor):
            editor = self.create_editor_tab(make_current=True)
        return self.load_file(editor, path)

    def file_save(self, editor=None):
        editor = editor or self.current_editor()
        if not editor:
            return False
        if not editor.file_path:
            return self.file_save_as(editor=editor)
        try:
            with open(editor.file_path, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")
            return False
        editor.document().setModified(False)
        self.on_editor_modified(editor)
        if editor is self.current_editor():
            self.statusBar().showMessage(f"Сохранен файл: {editor.file_path}", 2000)
        return True

    def file_save_as(self, editor=None):
        editor = editor or self.current_editor()
        if not editor:
            return False
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить как", "", "Текстовые файлы (*.txt);;Все файлы (*)")
        if not path:
            return False
        editor.file_path = path
        return self.file_save(editor=editor)

    def load_file(self, editor, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")
            return False
        editor.setPlainText(data)
        editor.document().setModified(False)
        editor.file_path = path
        self.on_editor_modified(editor)
        if editor is self.current_editor():
            self.statusBar().showMessage(f"Открыт файл: {path}", 2000)
        return True

    def edit_undo(self):
        editor = self.current_editor()
        if editor:
            editor.undo()

    def edit_redo(self):
        editor = self.current_editor()
        if editor:
            editor.redo()

    def edit_cut(self):
        editor = self.current_editor()
        if editor:
            editor.cut()

    def edit_copy(self):
        editor = self.current_editor()
        if editor:
            editor.copy()

    def edit_paste(self):
        editor = self.current_editor()
        if editor:
            editor.paste()

    def edit_select_all(self):
        editor = self.current_editor()
        if editor:
            editor.selectAll()

    def edit_delete(self):
        editor = self.current_editor()
        if not editor:
            return
        cursor = editor.textCursor()
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
        return size

    def change_editor_font_size(self, delta):
        editor = self.current_editor()
        if not editor:
            return
        new_size = self.change_font_size(editor, delta)
        for i in range(self.editor_tabs.count()):
            other = self.editor_tabs.widget(i)
            if other is editor or not isinstance(other, CodeEditor):
                continue
            font = QFont(other.font())
            font.setPointSize(new_size)
            other.setFont(font)

    def change_output_font_size(self, delta):
        new_size = self.change_font_size(self.output_text, delta)
        font = QFont(self.output_errors.font())
        font.setPointSize(new_size)
        self.output_errors.setFont(font)
        self.output_errors.horizontalHeader().setFont(font)

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
        editor = self.current_editor()
        if not editor:
            return
        text = editor.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("Пустой текст. Нечего анализировать.")
            self.fill_errors_table([])
            self.output_tabs.setCurrentWidget(self.output_text)
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

        self.output_text.setPlainText("\n".join(result_lines))
        self.fill_errors_table(errors)
        if errors:
            self.output_tabs.setCurrentWidget(self.output_errors)
        else:
            self.output_tabs.setCurrentWidget(self.output_text)
        self.statusBar().showMessage("Анализ завершен", 2000)

    def fill_errors_table(self, errors):
        self.output_errors.setRowCount(0)
        for row, (line_no, col_no, msg) in enumerate(errors):
            self.output_errors.insertRow(row)
            self.output_errors.setItem(row, 0, QTableWidgetItem(str(line_no)))
            self.output_errors.setItem(row, 1, QTableWidgetItem(str(col_no)))
            self.output_errors.setItem(row, 2, QTableWidgetItem(msg))

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

    def update_cursor_status(self):
        editor = self.current_editor()
        if not editor:
            return
        cursor = editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        name = editor.file_path or f"Безымянный {editor.untitled_id}"
        self.statusBar().showMessage(f"{name} | Строка {line}, столбец {col}")

    def update_title(self):
        editor = self.current_editor()
        if not editor:
            self.setWindowTitle("Редактор")
            return
        if editor.file_path:
            name = editor.file_path
        else:
            name = f"Безымянный {editor.untitled_id}"
        mod = "*" if editor.document().isModified() else ""
        self.setWindowTitle(f"Редактор {name}{mod}")
        self.update_cursor_status()

    def closeEvent(self, event):
        for i in range(self.editor_tabs.count()):
            self.editor_tabs.setCurrentIndex(i)
            editor = self.editor_tabs.widget(i)
            if isinstance(editor, CodeEditor) and not self.maybe_save(editor):
                event.ignore()
                return
        event.accept()

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
        opened = False
        for url in urls:
            if self.open_path(url.toLocalFile()):
                opened = True
        if opened:
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
