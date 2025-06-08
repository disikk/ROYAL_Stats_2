from PyQt6 import QtWidgets
from typing import Optional

class SessionSelectDialog(QtWidgets.QDialog):
    """Dialog for choosing existing session or creating a new one."""

    def __init__(self, app_service, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        self.selected_session_id: Optional[str] = None
        self.new_session_name: str = ""

        self.setWindowTitle("Выбор сессии")
        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel("Выберите существующую сессию или создайте новую")
        layout.addWidget(label)

        self.combo = QtWidgets.QComboBox()
        self.combo.addItem("Новая сессия...", userData=None)
        for sess in self.app_service.get_all_sessions():
            self.combo.addItem(sess.session_name, userData=sess.session_id)
        self.combo.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self.combo)

        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("Имя новой сессии")
        layout.addWidget(self.name_edit)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._on_combo_changed(0)

    def _on_combo_changed(self, index):
        session_id = self.combo.currentData()
        self.name_edit.setVisible(session_id is None)

    def get_result(self):
        session_id = self.combo.currentData()
        name = self.name_edit.text().strip()
        return session_id, name
