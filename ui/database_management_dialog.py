# -*- coding: utf-8 -*-

"""
Диалог для управления базами данных (выбор существующей, создание новой, удаление).
"""

from PyQt6 import QtWidgets, QtGui, QtCore
import os
import logging

import config
from application_service import ApplicationService # Импортируем сервис

logger = logging.getLogger('ROYAL_Stats.DatabaseManagementDialog')
logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

class DatabaseManagementDialog(QtWidgets.QDialog):
    """
    Диалог для выбора существующей БД или создания новой.
    """
    def __init__(self, parent=None, app_service: ApplicationService = None):
        super().__init__(parent)
        self.app_service = app_service # Используем ApplicationService
        self.setWindowTitle("Управление базами данных")
        self.setMinimumWidth(400)

        layout = QtWidgets.QVBoxLayout(self)

        # Список существующих баз данных
        layout.addWidget(QtWidgets.QLabel("Выберите базу данных:"))
        self.db_list_widget = QtWidgets.QListWidget()
        self._populate_db_list() # Заполняем список
        self.db_list_widget.itemDoubleClicked.connect(self._accept_selection) # Двойной клик открывает
        layout.addWidget(self.db_list_widget)

        # Кнопка "Открыть выбранную"
        self.open_button = QtWidgets.QPushButton("Открыть выбранную")
        self.open_button.clicked.connect(self._accept_selection)
        layout.addWidget(self.open_button)

        # Кнопка "Удалить выбранную"
        self.delete_button = QtWidgets.QPushButton("Удалить выбранную БД")
        self.delete_button.clicked.connect(self._delete_selected_db)
        layout.addWidget(self.delete_button)

        layout.addSpacing(20) # Разделитель

        # Создание новой базы данных
        layout.addWidget(QtWidgets.QLabel("Создать новую базу данных:"))
        new_db_layout = QtWidgets.QHBoxLayout()
        self.new_db_name_edit = QtWidgets.QLineEdit()
        self.new_db_name_edit.setPlaceholderText("Имя новой БД (без расширения .db)")
        new_db_layout.addWidget(self.new_db_name_edit)

        self.create_db_button = QtWidgets.QPushButton("Создать")
        self.create_db_button.clicked.connect(self._accept_creation)
        new_db_layout.addWidget(self.create_db_button)
        layout.addLayout(new_db_layout)

        # Кнопка "Отмена" или "Закрыть"
        self.close_button = QtWidgets.QPushButton("Закрыть")
        self.close_button.clicked.connect(self.reject) # reject() закрывает диалог с результатом QDialog.Rejected
        layout.addWidget(self.close_button)

        self.setLayout(layout)
        self.resize(450, 350) # Установим размер по умолчанию

    def _populate_db_list(self):
        """Заполняет список доступных файлов баз данных."""
        self.db_list_widget.clear()
        available_dbs = self.app_service.get_available_databases()

        for db_name in available_dbs:
            list_item = QtWidgets.QListWidgetItem(db_name)
            db_full_path = os.path.join(config.DEFAULT_DB_DIR, db_name)

            # Отмечаем текущую БД
            if db_full_path == self.app_service.db_path:
                font = list_item.font()
                font.setBold(True)
                list_item.setFont(font)
                list_item.setText(f"{db_name} (текущая)")

            self.db_list_widget.addItem(list_item)

    @QtCore.pyqtSlot()
    def _accept_selection(self):
        """Обрабатывает выбор существующей БД."""
        selected_items = self.db_list_widget.selectedItems()
        if selected_items:
            # Извлекаем имя файла, убирая пометку "(текущая)"
            db_name = selected_items[0].text().replace(" (текущая)", "").strip()
            db_full_path = os.path.join(config.DEFAULT_DB_DIR, db_name)

            # Проверяем, не выбрана ли уже текущая БД
            if db_full_path == self.app_service.db_path:
                 self.accept() # Просто закрываем диалог, если БД не изменилась
                 return

            try:
                self.app_service.switch_database(db_full_path)
                self.accept() # Закрываем диалог с результатом QDialog.Accepted
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка подключения", f"Не удалось подключиться к БД '{db_name}':\n{e}")
                logger.error(f"Не удалось подключиться к БД {db_full_path}: {e}")


    @QtCore.pyqtSlot()
    def _accept_creation(self):
        """Обрабатывает запрос на создание новой БД."""
        new_name = self.new_db_name_edit.text().strip()
        if not new_name:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите имя для новой базы данных.")
            return

        # Проверяем, что имя не содержит запрещенных символов или путей
        if any(c in new_name for c in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
             QtWidgets.QMessageBox.warning(self, "Ошибка", "Имя базы данных содержит недопустимые символы.")
             return

        if not new_name.lower().endswith(".db"):
            new_name += ".db"

        # Проверяем, существует ли файл с таким именем
        new_db_path = os.path.join(config.DEFAULT_DB_DIR, new_name)
        if os.path.exists(new_db_path):
             QtWidgets.QMessageBox.warning(self, "Ошибка", f"Файл '{new_name}' уже существует.")
             return

        try:
            self.app_service.create_new_database(new_name)
            self.accept() # Закрываем диалог с результатом QDialog.Accepted
        except FileExistsError:
             # Эту ошибку мы уже обработали выше, но на всякий случай
             QtWidgets.QMessageBox.warning(self, "Ошибка", f"Файл '{new_name}' уже существует.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка создания", f"Не удалось создать БД '{new_name}':\n{e}")
            logger.error(f"Не удалось создать БД {new_db_path}: {e}")


    @QtCore.pyqtSlot()
    def _delete_selected_db(self):
        """Обрабатывает запрос на удаление выбранной БД."""
        selected_items = self.db_list_widget.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.information(self, "Удаление БД", "Выберите базу данных для удаления.")
            return

        db_name = selected_items[0].text().replace(" (текущая)", "").strip()
        db_full_path = os.path.join(config.DEFAULT_DB_DIR, db_name)

        # Проверяем, не пытается ли пользователь удалить текущую БД
        if db_full_path == self.app_service.db_path:
            QtWidgets.QMessageBox.warning(self, "Ошибка удаления", "Невозможно удалить базу данных, которая сейчас используется.")
            return

        # Запрос подтверждения
        reply = QtWidgets.QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите безвозвратно удалить базу данных '{db_name}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No # Ответ по умолчанию
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                os.remove(db_full_path)
                logger.info(f"База данных удалена: {db_full_path}")
                self._populate_db_list() # Обновляем список после удаления
                QtWidgets.QMessageBox.information(self, "Удаление БД", f"База данных '{db_name}' успешно удалена.")
            except OSError as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка удаления", f"Не удалось удалить файл БД '{db_name}':\n{e}")
                logger.error(f"Не удалось удалить файл БД {db_full_path}: {e}")
            except Exception as e:
                 QtWidgets.QMessageBox.critical(self, "Ошибка удаления", f"Произошла неизвестная ошибка при удалении БД '{db_name}':\n{e}")
                 logger.error(f"Неизвестная ошибка при удалении БД {db_full_path}: {e}")