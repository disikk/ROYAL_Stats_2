# -*- coding: utf-8 -*-

"""
Диалог управления базами данных для Royal Stats.
Позволяет переключаться между БД, создавать новые и удалять существующие.
"""

from PyQt6 import QtWidgets, QtCore, QtGui
import os
import logging
from typing import Optional, List

from services import AppFacade

logger = logging.getLogger('ROYAL_Stats.DatabaseDialog')


class DatabaseManagementDialog(QtWidgets.QDialog):
    """Диалог для управления базами данных."""
    
    def __init__(self, parent=None, app_service: AppFacade = None):
        super().__init__(parent)
        self.app_service = app_service
        self.selected_db_path = None
        self.sort_mode = "name"  # name or date
        self.all_db_paths: List[str] = []  # Храним полный список БД для фильтрации
        self._init_ui()
        self._load_databases()
        
    def _init_ui(self):
        """Инициализирует интерфейс диалога."""
        self.setWindowTitle("Управление базами данных")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        header = QtWidgets.QLabel("Выберите базу данных или создайте новую")
        header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #FAFAFA;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(header)

        # Сортировка
        sort_layout = QtWidgets.QHBoxLayout()
        sort_label = QtWidgets.QLabel("Сортировка:")
        sort_label.setStyleSheet("QLabel { color: #FAFAFA; }")
        self.sort_combo = QtWidgets.QComboBox()
        self.sort_combo.addItem("По имени", userData="name")
        self.sort_combo.addItem("По дате", userData="date")
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        sort_layout.addWidget(sort_label)
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        layout.addLayout(sort_layout)

        # Поиск
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("Поиск:")
        search_label.setStyleSheet("QLabel { color: #FAFAFA; }")
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Введите имя БД")
        self.search_edit.textChanged.connect(self._apply_filter)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # Список баз данных
        self.db_list = QtWidgets.QListWidget()
        self.db_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.db_list.setStyleSheet("""
            QListWidget {
                background-color: #27272A;
                border: 1px solid #3F3F46;
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #3B82F6;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #52525B;
                color: #FFD700;
            }
        """)
        self.db_list.itemDoubleClicked.connect(self._on_db_double_clicked)
        self.db_list.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.db_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.db_list)
        
        # Информация о выбранной БД
        self.info_label = QtWidgets.QLabel("")
        self.info_label.setStyleSheet("""
            QLabel {
                color: #A1A1AA;
                font-size: 12px;
                padding: 8px;
                background-color: #27272A;
                border-radius: 4px;
                border: 1px solid #3F3F46;
            }
        """)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Кнопки управления
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.new_db_btn = QtWidgets.QPushButton("Создать новую БД")
        self.new_db_btn.setIcon(QtGui.QIcon.fromTheme("document-new"))
        self.new_db_btn.clicked.connect(self._create_new_database)
        button_layout.addWidget(self.new_db_btn)
        
        self.delete_db_btn = QtWidgets.QPushButton("Удалить выбранные БД")
        self.delete_db_btn.setIcon(QtGui.QIcon.fromTheme("edit-delete"))
        self.delete_db_btn.clicked.connect(self._delete_database)
        self.delete_db_btn.setEnabled(False)  # Активируется при выборе БД
        self.delete_db_btn.setStyleSheet("""
            QPushButton:enabled {
                background-color: #DC2626;
            }
            QPushButton:enabled:hover {
                background-color: #EF4444;
            }
        """)
        button_layout.addWidget(self.delete_db_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Разделитель
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { background-color: #3F3F46; max-height: 1px; }")
        layout.addWidget(separator)
        
        # Кнопки диалога
        dialog_buttons = QtWidgets.QHBoxLayout()
        
        self.select_btn = QtWidgets.QPushButton("Выбрать")
        self.select_btn.setDefault(True)
        self.select_btn.clicked.connect(self._select_database)
        self.select_btn.setEnabled(False)  # Активируется при выборе БД
        dialog_buttons.addWidget(self.select_btn)
        
        self.cancel_btn = QtWidgets.QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addWidget(self.cancel_btn)
        
        layout.addLayout(dialog_buttons)
        
        # Подключаем сигналы
        self.db_list.itemSelectionChanged.connect(self._on_selection_changed)
        
    def _load_databases(self):
        """Загружает список доступных баз данных."""
        self.db_list.clear()
        db_files = self.app_service.get_available_databases()
        current_db = self.app_service.db_path

        # Сортируем список в зависимости от выбранного режима
        other_dbs = [p for p in db_files if p != current_db]
        if self.sort_mode == "date":
            other_dbs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        else:
            other_dbs.sort(key=lambda x: os.path.basename(x).lower())

        self.all_db_paths = [current_db] + other_dbs if current_db in db_files else other_dbs
        self._apply_filter()

    def _on_sort_changed(self):
        """Обновляет список при смене сортировки."""
        mode = self.sort_combo.currentData()
        if mode:
            self.sort_mode = mode
        self._load_databases()

    def _apply_filter(self):
        """Применяет текстовый фильтр к списку БД."""
        search = self.search_edit.text().strip().lower()
        self.db_list.clear()
        current_db = self.app_service.db_path
        for db_path in self.all_db_paths:
            db_name = os.path.basename(db_path)
            if search in db_name.lower():
                item = QtWidgets.QListWidgetItem(db_name)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, db_path)
                if db_path == current_db:
                    item.setText(f"{db_name} (текущая)")
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.db_list.addItem(item)

        if self.db_list.count() > 0:
            self.db_list.setCurrentRow(0)
            
    def _on_selection_changed(self):
        """Обработчик изменения выбора в списке."""
        selected_items = self.db_list.selectedItems()

        if len(selected_items) == 1:
            item = selected_items[0]
            db_path = item.data(QtCore.Qt.ItemDataRole.UserRole)
            self.selected_db_path = db_path

            try:
                file_size = os.path.getsize(db_path) / 1024 / 1024
                file_time = os.path.getmtime(db_path)
                from datetime import datetime
                mod_date = datetime.fromtimestamp(file_time).strftime("%d.%m.%Y %H:%M")

                self.info_label.setText(
                    f"Путь: {db_path}\n"
                    f"Размер: {file_size:.2f} МБ\n"
                    f"Изменен: {mod_date}"
                )
            except Exception as e:
                self.info_label.setText(f"Ошибка получения информации: {e}")

            self.select_btn.setEnabled(True)
            is_current = db_path == self.app_service.db_path
            self.delete_db_btn.setEnabled(not is_current)

        elif len(selected_items) > 1:
            self.selected_db_path = None
            self.info_label.setText(f"Выбрано {len(selected_items)} баз данных")
            self.select_btn.setEnabled(False)
            is_current_selected = any(
                item.data(QtCore.Qt.ItemDataRole.UserRole) == self.app_service.db_path
                for item in selected_items
            )
            self.delete_db_btn.setEnabled(not is_current_selected)

        else:
            self.selected_db_path = None
            self.info_label.setText("")
            self.select_btn.setEnabled(False)
            self.delete_db_btn.setEnabled(False)
            
    def _on_db_double_clicked(self, item):
        """Обработчик двойного клика по БД."""
        if item:
            self._select_database()
            
    def _select_database(self):
        """Выбирает БД и закрывает диалог."""
        if self.selected_db_path and self.selected_db_path != self.app_service.db_path:
            try:
                # Загружаем новую БД без синхронного пересчёта статистики
                self.app_service.switch_database(self.selected_db_path, load_stats=False)
                self.accept()
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось переключиться на базу данных:\n{e}"
                )
        else:
            self.accept()
            
    def _create_new_database(self):
        """Создает новую базу данных."""
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Новая база данных",
            "Введите имя для новой базы данных:",
            QtWidgets.QLineEdit.EchoMode.Normal,
            f"royal_stats_{QtCore.QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.db"
        )
        
        if ok and name:
            # Убеждаемся, что имя заканчивается на .db
            if not name.endswith('.db'):
                name += '.db'
                
            try:
                self.app_service.create_new_database(name)
                # Принудительно обновляем список БД
                self._load_databases()
                # Находим и выбираем созданную БД
                for i in range(self.db_list.count()):
                    item = self.db_list.item(i)
                    item_path = item.data(QtCore.Qt.ItemDataRole.UserRole)
                    if item_path and name in os.path.basename(item_path):
                        self.db_list.setCurrentItem(item)
                        break
                
                QtWidgets.QMessageBox.information(
                    self,
                    "Успех",
                    f"База данных '{name}' успешно создана и выбрана."
                )

                # Закрываем диалог, чтобы основное окно сразу обновило статистику
                # (MainWindow.compare db_path и вызовет refresh_all_data)
                self.accept()
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось создать базу данных:\n{e}"
                )
                
    def _delete_database(self):
        """Удаляет выбранные базы данных."""
        selected_items = self.db_list.selectedItems()
        if not selected_items:
            return

        db_paths = [item.data(QtCore.Qt.ItemDataRole.UserRole) for item in selected_items]

        # Нельзя удалять текущую БД
        if self.app_service.db_path in db_paths:
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Нельзя удалить текущую базу данных."
            )
            return

        db_names = [os.path.basename(p) for p in db_paths]
        names_list = "\n".join(db_names)

        reply = QtWidgets.QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить следующие базы данных:\n{names_list}\n\n"
            "Это действие необратимо!",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            errors = []
            for path in db_paths:
                try:
                    os.remove(path)
                except Exception as e:
                    errors.append(f"{os.path.basename(path)}: {e}")

            self._load_databases()

            if not errors:
                QtWidgets.QMessageBox.information(
                    self,
                    "Успех",
                    "Выбранные базы данных успешно удалены."
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Частичная ошибка",
                    "Не удалось удалить следующие БД:\n" + "\n".join(errors)
                )

    def _show_context_menu(self, position: QtCore.QPoint):
        """Отображает контекстное меню для списка баз данных."""
        selected_items = self.db_list.selectedItems()
        if len(selected_items) != 1:
            return

        menu = QtWidgets.QMenu(self)
        rename_action = menu.addAction("Переименовать БД")

        action = menu.exec(self.db_list.viewport().mapToGlobal(position))
        if action == rename_action:
            self._rename_database(selected_items[0])

    def _rename_database(self, item: QtWidgets.QListWidgetItem):
        """Переименовывает выбранную базу данных."""
        old_path = item.data(QtCore.Qt.ItemDataRole.UserRole)
        old_name = os.path.basename(old_path)

        new_name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Переименование БД",
            "Введите новое имя базы данных:",
            QtWidgets.QLineEdit.EchoMode.Normal,
            old_name,
        )

        if ok and new_name and new_name != old_name:
            try:
                new_path = self.app_service.rename_database(old_path, new_name)
                self._load_databases()
                # Выбрать переименованную БД в списке
                for i in range(self.db_list.count()):
                    it = self.db_list.item(i)
                    if it.data(QtCore.Qt.ItemDataRole.UserRole) == new_path:
                        self.db_list.setCurrentItem(it)
                        break
                QtWidgets.QMessageBox.information(
                    self,
                    "Успех",
                    f"База данных успешно переименована в '{os.path.basename(new_path)}'.",
                )
            except FileExistsError as e:
                QtWidgets.QMessageBox.warning(self, "Ошибка", str(e))
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось переименовать базу данных:\n{e}",
                )
