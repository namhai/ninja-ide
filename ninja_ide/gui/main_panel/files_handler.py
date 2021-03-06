# -*- coding: utf-8 -*-
#
# This file is part of NINJA-IDE (http://ninja-ide.org).
#
# NINJA-IDE is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# any later version.
#
# NINJA-IDE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NINJA-IDE; If not, see <http://www.gnu.org/licenses/>.
from __future__ import absolute_import
from __future__ import unicode_literals

import uuid

from ninja_ide.tools.logger import NinjaLogger
logger = NinjaLogger(__name__)

from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtDeclarative import QDeclarativeView

from ninja_ide.gui.ide import IDE
from ninja_ide.tools import ui_tools


class FilesHandler(QFrame):

    def __init__(self, parent=None):
        super(FilesHandler, self).__init__(
            None, Qt.FramelessWindowHint | Qt.Popup)
        self._main_container = parent
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")
        # Create the QML user interface.
        self.view = QDeclarativeView()
        self.view.setResizeMode(QDeclarativeView.SizeRootObjectToView)
        self.view.setSource(ui_tools.get_qml_resource("FilesHandler.qml"))
        self._root = self.view.rootObject()
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(self.view)

        self._model = {}
        self._temp_files = {}
        self._max_index = 0

        self.connect(self._root, SIGNAL("open(QString, QString)"), self._open)
        self.connect(self._root, SIGNAL("close(QString, QString)"), self._close)
        self.connect(self._root, SIGNAL("hide()"), self.hide)

    def _open(self, path, temp):
        if temp:
            nfile = self._temp_files[temp]
            ninjaide = IDE.get_service("ide")
            neditable = ninjaide.get_or_create_editable(nfile=nfile)
            self._main_container.current_widget.set_current(neditable)
        else:
            self._main_container.open_file(path)
            index = self._model[path]
            self._max_index = max(self._max_index, index) + 1
            self._model[path] = self._max_index
        self.hide()

    def _close(self, path, temp):
        if temp:
            nfile = self._temp_files.get(temp, None)
        else:
            ninjaide = IDE.get_service("ide")
            nfile = ninjaide.get_or_create_nfile(path)
        if nfile is not None:
            nfile.close()

    def _add_model(self):
        ninjaide = IDE.get_service("ide")
        files = ninjaide.opened_files
        # Update model
        old = set(self._model.keys())
        new = set([nfile.file_path for nfile in files])
        result = old - new
        for item in result:
            del self._model[item]
        current_editor = self._main_container.get_current_editor()
        current_path = None
        if current_editor:
            current_path = current_editor.file_path
        model = []
        for nfile in files:
            if (nfile.file_path not in self._model and
                    nfile.file_path is not None):
                self._model[nfile.file_path] = 0
            neditable = ninjaide.get_or_create_editable(nfile=nfile)
            checkers = neditable.sorted_checkers
            checks = []
            for items in checkers:
                checker, color, _ = items
                if checker.dirty:
                    checks.append(
                        {"checker_text": checker.dirty_text,
                         "checker_color": color})
            modified = neditable.document.isModified()
            temp_file = str(uuid.uuid4()) if nfile.file_path is None else ""
            filepath = nfile.file_path if nfile.file_path is not None else ""
            model.append([nfile.file_name, filepath, checks, modified,
                          temp_file])
            if temp_file:
                self._temp_files[temp_file] = nfile
        if current_path:
            index = self._model[current_path]
            self._max_index = max(self._max_index, index) + 1
            self._model[current_path] = self._max_index
        model = sorted(model, key=lambda x: self._model.get(x[1], False),
                       reverse=True)
        self._root.set_model(model)

    def showEvent(self, event):
        self._add_model()
        width = max(self._main_container.width() / 3, 300)
        logger.debug("This is the width")
        logger.debug(width)
        height = max(self._main_container.height() / 2, 400)
        logger.debug("This is the height")
        logger.debug(height)
        self.view.setFixedWidth(width)

        self.view.setFixedHeight(height)
        super(FilesHandler, self).showEvent(event)
        self._root.show_animation()
        point = self._main_container.mapToGlobal(self.view.pos())
        y_diff = self._main_container.combo_header_size
        self.move(point.x(), point.y() + y_diff)
        self.view.setFocus()
        self._root.activateInput()

    def hideEvent(self, event):
        super(FilesHandler, self).hideEvent(event)
        self._temp_files = {}
        self._root.clear_model()

    def next_item(self):
        if not self.isVisible():
            self.show()
        self._root.next_item()

    def previous_item(self):
        if not self.isVisible():
            self.show()
        self._root.previous_item()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        elif (event.modifiers() == Qt.ControlModifier and
                event.key() == Qt.Key_PageDown) or event.key() == Qt.Key_Down:
            self._root.next_item()
        elif (event.modifiers() == Qt.ControlModifier and
                event.key() == Qt.Key_PageUp) or event.key() == Qt.Key_Up:
            self._root.previous_item()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._root.open_item()
        super(FilesHandler, self).keyPressEvent(event)
