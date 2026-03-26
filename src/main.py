import sys
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import Qt, QRegularExpression, QSize, QRect
from PySide6.QtGui import (
    QAction,
    QActionGroup,
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


@dataclass
class Lexeme:
    code: int
    token_type: str
    lexeme: str
    line: int
    start_col: int
    end_col: int
    is_error: bool = False
    message: str = ""


class LexicalAnalyzer:
    TOKEN_TYPES = {
        "INTEGER": (1, "целое без знака"),
        "IDENTIFIER": (2, "идентификатор"),
        "ATOM": (3, "атом"),
        "STRING": (4, "строковый литерал"),
        "ASSIGN": (10, "оператор присваивания"),
        "COMMA": (11, "разделитель (запятая)"),
        "TUPLE_OPEN": (12, "разделитель (открывающая скобка кортежа)"),
        "TUPLE_CLOSE": (13, "разделитель (закрывающая скобка кортежа)"),
        "WHITESPACE": (14, "разделитель (пробел/табуляция)"),
        "NEWLINE": (15, "разделитель (перенос строки)"),
        "SEMICOLON": (16, "конец оператора"),
        "ERROR": (99, "ошибка"),
    }

    SINGLE_CHAR_TOKENS = {
        "=": "ASSIGN",
        ",": "COMMA",
        "{": "TUPLE_OPEN",
        "}": "TUPLE_CLOSE",
        ";": "SEMICOLON",
    }

    def analyze(self, text):
        result = []
        i = 0
        line = 1
        col = 1
        n = len(text)

        while i < n:
            ch = text[i]
            start_i = i
            start_col = col

            if ch == "\n":
                self._push_token(result, "NEWLINE", "\n", line, col, col)
                i += 1
                line += 1
                col = 1
                continue

            if ch in " \t\r":
                while i < n and text[i] in " \t\r":
                    i += 1
                    col += 1
                self._push_token(result, "WHITESPACE", text[start_i:i], line, start_col, col - 1)
                continue

            if ch.isdigit():
                while i < n and text[i].isdigit():
                    i += 1
                    col += 1
                self._push_token(result, "INTEGER", text[start_i:i], line, start_col, col - 1)
                continue

            if self._is_identifier_start(ch):
                while i < n and self._is_identifier_part(text[i]):
                    i += 1
                    col += 1
                self._push_token(result, "IDENTIFIER", text[start_i:i], line, start_col, col - 1)
                continue

            if ch == ":":
                i += 1
                col += 1
                if i < n and self._is_identifier_start(text[i]):
                    atom_start = i
                    while i < n and self._is_identifier_part(text[i]):
                        i += 1
                        col += 1
                    self._push_token(result, "ATOM", ":" + text[atom_start:i], line, start_col, col - 1)
                else:
                    self._push_error(
                        result,
                        ":",
                        line,
                        start_col,
                        start_col,
                        "после ':' ожидается имя атома",
                    )
                continue

            if ch == '"':
                i += 1
                col += 1
                escaped = False
                closed = False
                while i < n:
                    curr = text[i]
                    if curr == "\n":
                        break
                    if escaped:
                        escaped = False
                        i += 1
                        col += 1
                        continue
                    if curr == "\\":
                        escaped = True
                        i += 1
                        col += 1
                        continue
                    if curr == '"':
                        i += 1
                        col += 1
                        closed = True
                        break
                    i += 1
                    col += 1

                if closed:
                    self._push_token(result, "STRING", text[start_i:i], line, start_col, col - 1)
                else:
                    end_col = max(start_col, col - 1)
                    self._push_error(
                        result,
                        text[start_i:i],
                        line,
                        start_col,
                        end_col,
                        "незакрытый строковый литерал",
                    )
                continue

            token_name = self.SINGLE_CHAR_TOKENS.get(ch)
            if token_name:
                self._push_token(result, token_name, ch, line, col, col)
                i += 1
                col += 1
                continue

            error_start = i
            while i < n and not self._is_token_start(text[i]):
                i += 1
                col += 1
            invalid_part = text[error_start:i]
            if len(invalid_part) == 1:
                message = f"недопустимый символ '{invalid_part}'"
            else:
                message = f"недопустимая последовательность '{invalid_part}'"
            self._push_error(result, invalid_part, line, start_col, col - 1, message)

        return result

    def _push_token(self, collection, token_key, lexeme, line, start_col, end_col):
        code, token_type = self.TOKEN_TYPES[token_key]
        collection.append(
            Lexeme(
                code=code,
                token_type=token_type,
                lexeme=lexeme,
                line=line,
                start_col=start_col,
                end_col=end_col,
            )
        )

    def _push_error(self, collection, lexeme, line, start_col, end_col, message):
        code, token_type = self.TOKEN_TYPES["ERROR"]
        collection.append(
            Lexeme(
                code=code,
                token_type=token_type,
                lexeme=lexeme,
                line=line,
                start_col=start_col,
                end_col=end_col,
                is_error=True,
                message=message,
            )
        )

    @staticmethod
    def _is_identifier_start(ch):
        return ch == "_" or ("a" <= ch <= "z")

    @staticmethod
    def _is_identifier_part(ch):
        return ch == "_" or ch.isdigit() or ("a" <= ch <= "z")

    def _is_token_start(self, ch):
        if ch == "\n":
            return True
        if ch in " \t\r":
            return True
        if ch.isdigit():
            return True
        if self._is_identifier_start(ch):
            return True
        if ch == ":":
            return True
        if ch == '"':
            return True
        return ch in self.SINGLE_CHAR_TOKENS


@dataclass
class SyntaxIssue:
    fragment: str
    line: int
    col: int
    description: str


class SyntaxAnalyzer:
    CODE_INTEGER = 1
    CODE_IDENTIFIER = 2
    CODE_ATOM = 3
    CODE_STRING = 4
    CODE_ASSIGN = 10
    CODE_COMMA = 11
    CODE_TUPLE_OPEN = 12
    CODE_TUPLE_CLOSE = 13
    CODE_WHITESPACE = 14
    CODE_NEWLINE = 15
    CODE_SEMICOLON = 16

    def analyze(self, lexemes):
        self.tokens = [token for token in lexemes if token.code != self.CODE_WHITESPACE and not token.is_error]
        self.index = 0
        self.errors = []
        self.seen = set()

        if not self.tokens or all(token.code == self.CODE_NEWLINE for token in self.tokens):
            self._add_issue(None, "Ожидалось объявление кортежа")
            return self.errors

        self._parse_program()
        return self.errors

    def _parse_program(self):
        self._skip_newlines()
        while not self._at_end():
            self._parse_statement()
            self._skip_newlines()

    def _parse_statement(self):
        if self._code() != self.CODE_IDENTIFIER:
            self._add_issue(self._current(), "Ожидался идентификатор в начале объявления")
            self._synchronize({self.CODE_IDENTIFIER, self.CODE_NEWLINE})
            if self._code() != self.CODE_IDENTIFIER:
                return

        self._advance()

        if self._code() != self.CODE_ASSIGN:
            self._add_issue(self._current(), "Ожидался оператор '=' после идентификатора")
            # Локальная нейтрализация: считаем '=' вставленным и продолжаем.
        else:
            self._advance()

        self._parse_tuple()
        self._parse_statement_ending()

    def _parse_statement_ending(self):
        code = self._code()
        if code == self.CODE_SEMICOLON:
            self._advance()
            return
        if code == self.CODE_NEWLINE:
            self._add_issue(self._current(), "Ожидался ';' в конце строки")
            return
        if code in {None, self.CODE_IDENTIFIER}:
            self._add_issue(self._current(), "Ожидался ';' в конце объявления")
            return
        self._add_issue(self._current(), "Ожидался ';' в конце объявления")
        self._synchronize({self.CODE_SEMICOLON, self.CODE_NEWLINE, self.CODE_IDENTIFIER})
        if self._code() == self.CODE_SEMICOLON:
            self._advance()

    def _parse_tuple(self):
        if self._code() != self.CODE_TUPLE_OPEN:
            self._add_issue(self._current(), "Ожидалась '{' для начала кортежа")
            if self._code() in {None, self.CODE_NEWLINE}:
                return
        else:
            self._advance()

        if self._code() == self.CODE_TUPLE_CLOSE:
            self._advance()
            return

        expect_value = True
        while not self._at_end():
            code = self._code()
            token = self._current()

            if code == self.CODE_NEWLINE:
                self._add_issue(token, "Ожидалась '}' до конца строки")
                return

            if expect_value:
                if code == self.CODE_COMMA:
                    self._add_issue(token, "Пропущено значение кортежа перед запятой")
                    self._advance()
                    continue
                if code == self.CODE_TUPLE_CLOSE:
                    self._add_issue(token, "Пропущено значение кортежа перед '}'")
                    self._advance()
                    return
                if self._is_value_start(token):
                    self._parse_value()
                    expect_value = False
                    continue
                self._add_issue(token, "Ожидалось значение кортежа")
                self._synchronize({self.CODE_COMMA, self.CODE_TUPLE_CLOSE, self.CODE_NEWLINE})
                if self._code() == self.CODE_COMMA:
                    self._advance()
                    expect_value = True
                    continue
                if self._code() == self.CODE_TUPLE_CLOSE:
                    self._advance()
                    return
                return

            if code == self.CODE_COMMA:
                self._advance()
                expect_value = True
                continue
            if code == self.CODE_TUPLE_CLOSE:
                self._advance()
                return
            if self._is_value_start(token):
                self._add_issue(token, "Ожидалась ',' между элементами кортежа")
                # Локальная нейтрализация: считаем запятую вставленной.
                expect_value = True
                continue

            self._add_issue(token, "Ожидалась ',' или '}'")
            self._synchronize({self.CODE_COMMA, self.CODE_TUPLE_CLOSE, self.CODE_NEWLINE})
            if self._code() == self.CODE_COMMA:
                self._advance()
                expect_value = True
                continue
            if self._code() == self.CODE_TUPLE_CLOSE:
                self._advance()
            return

        self._add_issue(self._current(), "Ожидалась '}' в конце кортежа")

    def _parse_value(self):
        code = self._code()
        if code in {self.CODE_IDENTIFIER, self.CODE_ATOM, self.CODE_INTEGER, self.CODE_STRING}:
            self._advance()
            return True
        if code == self.CODE_TUPLE_OPEN:
            self._parse_tuple()
            return True
        self._add_issue(self._current(), "Ожидалось значение кортежа")
        if not self._at_end():
            self._advance()
        return False

    def _is_value_start(self, token):
        if not token:
            return False
        return token.code in {
            self.CODE_IDENTIFIER,
            self.CODE_ATOM,
            self.CODE_INTEGER,
            self.CODE_STRING,
            self.CODE_TUPLE_OPEN,
        }

    def _add_issue(self, token, description):
        if token is None:
            if self.tokens:
                last = self.tokens[-1]
                line = last.line
                col = last.end_col
                fragment = "EOF"
            else:
                line = 1
                col = 1
                fragment = "(пусто)"
        else:
            line = token.line
            col = token.start_col
            fragment = self._format_fragment(token)

        key = (line, col, description)
        if key in self.seen:
            return
        self.seen.add(key)
        self.errors.append(SyntaxIssue(fragment=fragment, line=line, col=col, description=description))

    def _format_fragment(self, token):
        if token.code == self.CODE_NEWLINE:
            return "\\n"
        return token.lexeme.replace("\n", "\\n").replace("\t", "\\t") or "(пусто)"

    def _synchronize(self, sync_codes):
        while not self._at_end() and self._code() not in sync_codes:
            self._advance()

    def _skip_newlines(self):
        while self._code() == self.CODE_NEWLINE:
            self._advance()

    def _current(self):
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def _code(self):
        token = self._current()
        if token is None:
            return None
        return token.code

    def _at_end(self):
        return self.index >= len(self.tokens)

    def _advance(self):
        if not self._at_end():
            self.index += 1


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
        bg = self.palette().window().color()
        painter.fillRect(event.rect(), bg)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                pen = self.palette().text().color()
                if bg.lightness() < 128:
                    pen = pen.lighter(140)
                else:
                    pen = pen.darker(130)
                painter.setPen(pen)
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
        base_color = self.palette().base().color()
        if base_color.lightness() < 128:
            line_color = base_color.lighter(120)
        else:
            line_color = base_color.darker(105)
        selection.format.setBackground(line_color)
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
        self.lang = "ru"
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
                "Грамматика объявления кортежа Elixir:\n\n"
                "<program>   -> <stmt_list>\n"
                "<stmt_list> -> <stmt> (<nl>+ <stmt>)*\n"
                "<stmt>      -> <id> '=' <tuple> ';'\n"
                "<tuple>     -> '{' <elems_opt> '}'\n"
                "<elems_opt> -> ε | <elems>\n"
                "<elems>     -> <value> (',' <value>)*\n"
                "<value>     -> <id> | <atom> | <int> | <string> | <tuple>"
            ),
            "Классификация грамматики": (
                "Используемая грамматика относится к контекстно-свободным (тип 2 по Хомскому).\n\n"
                "Слева в каждом правиле один нетерминал, а рекурсия в <value> -> <tuple> "
                "позволяет описывать вложенные кортежи."
            ),
            "Метод анализа": (
                "Реализована связка: лексический анализ + синтаксический анализ\n"
                "для варианта 'объявление кортежа на языке Elixir'.\n\n"
                "Парсер построен на рекурсивном спуске и использует нейтрализацию ошибок:\n"
                "при обнаружении синтаксической ошибки анализ не прерывается,\n"
                "а продолжается с точки синхронизации."
            ),
            "Тестовый пример": (
                "person = {:user, \"Andrey\", 21};\n"
                "coords = {10, 20, 30};\n"
                "status = {:ok, 200};\n"
                "bad = {:ok \"no-comma\", 1}\n"
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
        self.output_table = QTableWidget(0, 4)
        self.output_table.setHorizontalHeaderLabels(["Код", "Тип лексемы", "Лексема", "Местоположение"])
        self.output_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.output_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.output_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.output_table.verticalHeader().setVisible(False)
        self.output_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.output_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.output_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.output_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.output_table.cellClicked.connect(self.handle_result_row_click)
        self.output_syntax_table = QTableWidget(0, 3)
        self.output_syntax_table.setHorizontalHeaderLabels(["Неверный фрагмент", "Местоположение", "Описание"])
        self.output_syntax_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.output_syntax_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.output_syntax_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.output_syntax_table.verticalHeader().setVisible(False)
        self.output_syntax_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.output_syntax_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.output_syntax_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.output_syntax_table.cellClicked.connect(self.handle_syntax_row_click)
        self.output_tabs.addTab(self.output_text, "Результат")
        self.output_tabs.addTab(self.output_table, "Лексемы")
        self.output_tabs.addTab(self.output_syntax_table, "Синтаксис")

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
        self.apply_language()
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
        self.act_lang_ru = QAction("Русский", self)
        self.act_lang_en = QAction("English", self)
        self.act_lang_ru.setCheckable(True)
        self.act_lang_en.setCheckable(True)
        self.lang_group = QActionGroup(self)
        self.lang_group.setExclusive(True)
        self.lang_group.addAction(self.act_lang_ru)
        self.lang_group.addAction(self.act_lang_en)

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
        self.act_lang_ru.triggered.connect(lambda: self.set_language("ru"))
        self.act_lang_en.triggered.connect(lambda: self.set_language("en"))
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

        self.menu_lang = self.menuBar().addMenu("Язык")
        self.menu_lang.addAction(self.act_lang_ru)
        self.menu_lang.addAction(self.act_lang_en)

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
            name = f"{self.untitled_word()} {editor.untitled_id}"
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
        if self.lang == "en":
            msg.setWindowTitle("Unsaved Changes")
            msg.setText(f"Save changes to '{name}'?")
        else:
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
        font = QFont(self.output_table.font())
        font.setPointSize(new_size)
        self.output_table.setFont(font)
        self.output_table.horizontalHeader().setFont(font)
        self.output_syntax_table.setFont(font)
        self.output_syntax_table.horizontalHeader().setFont(font)

    def show_text_topic(self, title):
        sender = self.sender()
        dialog_title = sender.text() if isinstance(sender, QAction) else title
        dialog = TextInfoDialog(dialog_title, self.text_topics.get(title, ""), self)
        dialog.exec()

    def show_source_code(self):
        try:
            with open(__file__, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть исходный код:\n{e}")
            return
        dialog_title = "Program Source Code" if self.lang == "en" else "Исходный код программы"
        dialog = TextInfoDialog(dialog_title, text, self)
        dialog.exec()

    def run_analysis(self):
        editor = self.current_editor()
        if not editor:
            return
        text = editor.toPlainText()

        lexemes = LexicalAnalyzer().analyze(text)
        syntax_issues = SyntaxAnalyzer().analyze(lexemes)
        self.fill_result_table(lexemes)
        self.fill_syntax_table(syntax_issues)

        lexical_errors = [token for token in lexemes if token.is_error]
        syntax_errors = len(syntax_issues)
        total_errors = len(lexical_errors) + syntax_errors
        if self.lang == "en":
            lines_count = text.count("\n") + 1 if text else 0
            report = [
                "Lexical + syntax analysis result (Elixir tuple declaration)",
                f"Lines: {lines_count}",
                f"Characters: {len(text)}",
                f"Lexemes: {len(lexemes)}",
                f"Lexical errors: {len(lexical_errors)}",
                f"Syntax errors: {syntax_errors}",
                f"Total errors: {total_errors}",
                "",
            ]
            if lexical_errors:
                report.append("Lexical errors:")
                for token in lexical_errors:
                    report.append(f"L{token.line}:C{token.start_col} {token.message}")
                report.append("")
            if syntax_issues:
                report.append("Syntax errors:")
                for issue in syntax_issues:
                    report.append(f"L{issue.line}:C{issue.col} {issue.description}")
            if not lexical_errors and not syntax_issues:
                report.append("No errors found.")
        else:
            lines_count = text.count("\n") + 1 if text else 0
            report = [
                "Результаты лексического и синтаксического анализа (объявление кортежа на Elixir)",
                f"Строк: {lines_count}",
                f"Символов: {len(text)}",
                f"Лексем: {len(lexemes)}",
                f"Лексических ошибок: {len(lexical_errors)}",
                f"Синтаксических ошибок: {syntax_errors}",
                f"Общее количество ошибок: {total_errors}",
                "",
            ]
            if lexical_errors:
                report.append("Лексические ошибки:")
                for token in lexical_errors:
                    report.append(f"L{token.line}:C{token.start_col} {token.message}")
                report.append("")
            if syntax_issues:
                report.append("Синтаксические ошибки:")
                for issue in syntax_issues:
                    report.append(f"L{issue.line}:C{issue.col} {issue.description}")
            if not lexical_errors and not syntax_issues:
                report.append("Ошибок не найдено.")

        self.output_text.setPlainText("\n".join(report))
        if syntax_issues:
            self.output_tabs.setCurrentWidget(self.output_syntax_table)
        elif lexical_errors:
            self.output_tabs.setCurrentWidget(self.output_table)
        else:
            self.output_tabs.setCurrentWidget(self.output_text)
        status = "Analysis complete" if self.lang == "en" else "Анализ завершен"
        self.statusBar().showMessage(status, 2000)

    def fill_result_table(self, lexemes):
        self.output_table.setRowCount(0)
        for row, token in enumerate(lexemes):
            self.output_table.insertRow(row)
            token_type = token.token_type
            if token.is_error and token.message:
                token_type = f"{token.token_type}: {token.message}"

            values = [
                str(token.code),
                token_type,
                self.format_lexeme_for_table(token.lexeme),
                self.format_location_for_table(token),
            ]
            payload = (token.line, token.start_col, token.is_error)
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, payload)
                if token.is_error:
                    item.setForeground(QColor("#b00020"))
                self.output_table.setItem(row, col, item)

    def fill_syntax_table(self, issues):
        self.output_syntax_table.setRowCount(0)
        for row, issue in enumerate(issues):
            self.output_syntax_table.insertRow(row)
            values = [
                issue.fragment,
                self.format_syntax_location(issue),
                issue.description,
            ]
            payload = (issue.line, issue.col)
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, payload)
                item.setForeground(QColor("#b00020"))
                self.output_syntax_table.setItem(row, col, item)

    def format_lexeme_for_table(self, lexeme):
        if lexeme == "\n":
            return "(перенос строки)"
        if not lexeme:
            return "(пусто)"
        if all(ch in " \t\r" for ch in lexeme):
            parts = []
            spaces = lexeme.count(" ")
            tabs = lexeme.count("\t")
            if spaces:
                parts.append(f"пробел x{spaces}" if spaces > 1 else "пробел")
            if tabs:
                parts.append(f"табуляция x{tabs}" if tabs > 1 else "табуляция")
            if not parts:
                return "(разделитель)"
            return "(" + ", ".join(parts) + ")"
        return lexeme.replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")

    def format_location_for_table(self, token):
        if self.lang == "en":
            return f"line {token.line}, {token.start_col}-{token.end_col}"
        return f"строка {token.line}, {token.start_col}-{token.end_col}"

    def format_syntax_location(self, issue):
        if self.lang == "en":
            return f"line {issue.line}, position {issue.col}"
        return f"строка {issue.line}, позиция {issue.col}"

    def handle_result_row_click(self, row, _col):
        item = self.output_table.item(row, 0)
        if not item:
            return
        payload = item.data(Qt.UserRole)
        if not payload or len(payload) != 3:
            return
        line, col, is_error = payload
        if not is_error:
            return
        self.go_to_position(line, col)

    def handle_syntax_row_click(self, row, _col):
        item = self.output_syntax_table.item(row, 0)
        if not item:
            return
        payload = item.data(Qt.UserRole)
        if not payload or len(payload) != 2:
            return
        line, col = payload
        self.go_to_position(line, col)

    def go_to_position(self, line, col):
        editor = self.current_editor()
        if not editor:
            return
        block = editor.document().findBlockByNumber(max(0, line - 1))
        if not block.isValid():
            return
        pos = block.position() + max(0, col - 1)
        cursor = editor.textCursor()
        cursor.setPosition(pos)
        editor.setTextCursor(cursor)
        editor.setFocus()
        if self.lang == "en":
            self.statusBar().showMessage(f"Cursor moved to line {line}, column {col}", 2500)
        else:
            self.statusBar().showMessage(f"Курсор установлен: строка {line}, столбец {col}", 2500)

    def show_help(self):
        if self.lang == "en":
            text = (
                "File: new, open, save, save as, exit.\n"
                "Edit: undo/redo, cut/copy/paste, delete, select all.\n"
                "Text: study materials and program source code.\n"
                "Run: lexical + syntax analysis for Elixir tuple declaration (F5).\n"
                "Each declaration line must end with ';'.\n"
                "Help: function description and about dialog."
            )
            QMessageBox.information(self, "Help", text)
            return
        text = (
            "Файл: создать, открыть, сохранить, сохранить как, выход.\n"
            "Правка: отмена/повтор, вырезать/копировать/вставить, удалить, выделить все.\n"
            "Текст: учебные материалы и исходный код программы.\n"
            "Пуск: запуск лексического и синтаксического анализатора объявления кортежа Elixir (F5).\n"
            "Каждая строка объявления должна заканчиваться ';'.\n"
            "Справка: описание функций и окно о программе."
        )
        QMessageBox.information(self, "Справка", text)

    def show_about(self):
        if self.lang == "en":
            QMessageBox.information(self, "About", "GUI for a language processor. Lab work 3.")
            return
        QMessageBox.information(self, "О программе", "GUI для языкового процессора. Лабораторная работа 3.")

    def update_cursor_status(self):
        editor = self.current_editor()
        if not editor:
            return
        cursor = editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        name = editor.file_path or f"{self.untitled_word()} {editor.untitled_id}"
        if self.lang == "en":
            self.statusBar().showMessage(f"{name} | Line {line}, column {col}")
        else:
            self.statusBar().showMessage(f"{name} | Строка {line}, столбец {col}")

    def update_title(self):
        editor = self.current_editor()
        if not editor:
            self.setWindowTitle("Editor" if self.lang == "en" else "Редактор")
            return
        if editor.file_path:
            name = editor.file_path
        else:
            name = f"{self.untitled_word()} {editor.untitled_id}"
        mod = "*" if editor.document().isModified() else ""
        title = "Editor" if self.lang == "en" else "Редактор"
        self.setWindowTitle(f"{title} {name}{mod}")
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

    def untitled_word(self):
        return "Untitled" if self.lang == "en" else "Безымянный"

    def set_language(self, lang):
        if lang not in {"ru", "en"}:
            return
        if self.lang == lang:
            return
        self.lang = lang
        self.apply_language()

    def apply_language(self):
        ru = {
            "menu_file": "Файл",
            "menu_edit": "Правка",
            "menu_text": "Текст",
            "menu_help": "Справка",
            "menu_lang": "Язык",
            "menu_view": "Вид",
            "tb_quick": "Быстрые команды",
            "tb_tools": "Инструменты",
            "new": "Новый",
            "open": "Открыть...",
            "save": "Сохранить",
            "save_as": "Сохранить как...",
            "exit": "Выход",
            "undo": "Отменить",
            "redo": "Повторить",
            "cut": "Вырезать",
            "copy": "Копировать",
            "paste": "Вставить",
            "delete": "Удалить",
            "select_all": "Выделить все",
            "help": "Справка",
            "about": "О программе",
            "run": "Пуск",
            "editor_font_inc": "Шрифт редактора +",
            "editor_font_dec": "Шрифт редактора -",
            "output_font_inc": "Шрифт вывода +",
            "output_font_dec": "Шрифт вывода -",
            "topic_task": "Постановка задачи",
            "topic_grammar": "Грамматика",
            "topic_classification": "Классификация грамматики",
            "topic_method": "Метод анализа",
            "topic_example": "Тестовый пример",
            "topic_literature": "Список литературы",
            "topic_source": "Исходный код программы",
            "output_result": "Результат",
            "output_tokens": "Лексемы",
            "output_syntax": "Синтаксис",
            "output_placeholder": "Результаты анализа будут отображаться здесь",
            "token_col_code": "Код",
            "token_col_type": "Тип лексемы",
            "token_col_lexeme": "Лексема",
            "token_col_location": "Местоположение",
            "syntax_col_fragment": "Неверный фрагмент",
            "syntax_col_location": "Местоположение",
            "syntax_col_description": "Описание",
        }
        en = {
            "menu_file": "File",
            "menu_edit": "Edit",
            "menu_text": "Text",
            "menu_help": "Help",
            "menu_lang": "Language",
            "menu_view": "View",
            "tb_quick": "Quick Actions",
            "tb_tools": "Tools",
            "new": "New",
            "open": "Open...",
            "save": "Save",
            "save_as": "Save As...",
            "exit": "Exit",
            "undo": "Undo",
            "redo": "Redo",
            "cut": "Cut",
            "copy": "Copy",
            "paste": "Paste",
            "delete": "Delete",
            "select_all": "Select All",
            "help": "Help",
            "about": "About",
            "run": "Run",
            "editor_font_inc": "Editor Font +",
            "editor_font_dec": "Editor Font -",
            "output_font_inc": "Output Font +",
            "output_font_dec": "Output Font -",
            "topic_task": "Problem Statement",
            "topic_grammar": "Grammar",
            "topic_classification": "Grammar Classification",
            "topic_method": "Analysis Method",
            "topic_example": "Test Example",
            "topic_literature": "Literature",
            "topic_source": "Program Source Code",
            "output_result": "Result",
            "output_tokens": "Tokens",
            "output_syntax": "Syntax",
            "output_placeholder": "Analysis results will be shown here",
            "token_col_code": "Code",
            "token_col_type": "Token Type",
            "token_col_lexeme": "Lexeme",
            "token_col_location": "Location",
            "syntax_col_fragment": "Invalid Fragment",
            "syntax_col_location": "Location",
            "syntax_col_description": "Description",
        }
        t = ru if self.lang == "ru" else en

        self.menu_file.setTitle(t["menu_file"])
        self.menu_edit.setTitle(t["menu_edit"])
        self.menu_text.setTitle(t["menu_text"])
        self.menu_help.setTitle(t["menu_help"])
        self.menu_lang.setTitle(t["menu_lang"])
        self.menu_view.setTitle(t["menu_view"])

        self.toolbar_icons.setWindowTitle(t["tb_quick"])
        self.toolbar_text.setWindowTitle(t["tb_tools"])

        self.act_new.setText(t["new"])
        self.act_open.setText(t["open"])
        self.act_save.setText(t["save"])
        self.act_save_as.setText(t["save_as"])
        self.act_exit.setText(t["exit"])
        self.act_undo.setText(t["undo"])
        self.act_redo.setText(t["redo"])
        self.act_cut.setText(t["cut"])
        self.act_copy.setText(t["copy"])
        self.act_paste.setText(t["paste"])
        self.act_delete.setText(t["delete"])
        self.act_select_all.setText(t["select_all"])
        self.act_help.setText(t["help"])
        self.act_about.setText(t["about"])
        self.act_run.setText(t["run"])
        self.act_editor_font_inc.setText(t["editor_font_inc"])
        self.act_editor_font_dec.setText(t["editor_font_dec"])
        self.act_output_font_inc.setText(t["output_font_inc"])
        self.act_output_font_dec.setText(t["output_font_dec"])
        self.act_text_task.setText(t["topic_task"])
        self.act_text_grammar.setText(t["topic_grammar"])
        self.act_text_classification.setText(t["topic_classification"])
        self.act_text_method.setText(t["topic_method"])
        self.act_text_example.setText(t["topic_example"])
        self.act_text_literature.setText(t["topic_literature"])
        self.act_text_source.setText(t["topic_source"])

        self.act_lang_ru.setChecked(self.lang == "ru")
        self.act_lang_en.setChecked(self.lang == "en")

        self.output_tabs.setTabText(0, t["output_result"])
        self.output_tabs.setTabText(1, t["output_tokens"])
        self.output_tabs.setTabText(2, t["output_syntax"])
        self.output_text.setPlaceholderText(t["output_placeholder"])
        self.output_table.setHorizontalHeaderLabels(
            [
                t["token_col_code"],
                t["token_col_type"],
                t["token_col_lexeme"],
                t["token_col_location"],
            ]
        )
        self.output_syntax_table.setHorizontalHeaderLabels(
            [
                t["syntax_col_fragment"],
                t["syntax_col_location"],
                t["syntax_col_description"],
            ]
        )

        for i in range(self.editor_tabs.count()):
            self.update_editor_tab(i)
        self.update_title()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
