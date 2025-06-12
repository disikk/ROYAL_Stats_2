# -*- coding: utf-8 -*-

"""
Кастомные SVG иконки для приложения Royal Stats.
"""

from PyQt6 import QtGui, QtCore, QtSvg


class CustomIcons:
    """Класс для создания кастомных SVG иконок в плоском стиле."""
    
    @staticmethod
    def create_icon_from_svg(svg_content: str, color: str = "#E4E4E7") -> QtGui.QIcon:
        """Создает QIcon из SVG контента с заданным цветом."""
        # Заменяем плейсхолдер цвета
        svg_content = svg_content.replace("currentColor", color)
        
        # Создаем QSvgRenderer
        svg_bytes = svg_content.encode('utf-8')
        renderer = QtSvg.QSvgRenderer(svg_bytes)
        
        # Создаем pixmap и рисуем SVG
        pixmap = QtGui.QPixmap(24, 24)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        return QtGui.QIcon(pixmap)
    
    @staticmethod
    def refresh_icon(color: str = "#E4E4E7") -> QtGui.QIcon:
        """Иконка обновления (круговые стрелки)."""
        svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path fill="currentColor" d="M23.64 14.4q0 .08-.02.11q-1 4.16-4.16 6.74t-7.46 2.58q-2.27 0-4.38-.85T3.7 20.54l-2 2q-.29.29-.7.29t-.7-.29t-.29-.7V15q0-.4.29-.7t.7-.29h6.94q.4 0 .7.29t.29.7t-.29.7l-2.12 2.12q1.1 1.02 2.5 1.58t2.9.56q2.08 0 3.88-1.01t2.88-2.78q.17-.26.82-1.81q.12-.36.47-.36h2.98q.2 0 .35.15t.15.35m.39-12.4v6.94q0 .4-.29.7t-.7.29H16.1q-.4 0-.7-.29t-.29-.7t.29-.7l2.14-2.14Q16.44 4 12 4q-2.08 0-3.88 1.01T5.24 7.79q-.17.26-.82 1.81q-.12.36-.47.36H.78q-.2 0-.35-.15T.28 9.46v-.11q1.01-4.16 4.19-6.74T11.93 0q2.27 0 4.41.86t3.93 2.44l2.02-2q.29-.29.7-.29t.7.29t.29.7"/>
        </svg>'''
        return CustomIcons.create_icon_from_svg(svg, color)
    
    @staticmethod
    def database_icon(color: str = "#E4E4E7") -> QtGui.QIcon:
        """Иконка базы данных."""
        svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <ellipse cx="12" cy="5" rx="8" ry="3" stroke="currentColor" stroke-width="2"/>
            <path d="M4 5V19C4 20.6569 7.58172 22 12 22C16.4183 22 20 20.6569 20 19V5" 
                  stroke="currentColor" stroke-width="2"/>
            <path d="M4 12C4 13.6569 7.58172 15 12 15C16.4183 15 20 13.6569 20 12" 
                  stroke="currentColor" stroke-width="2"/>
        </svg>'''
        return CustomIcons.create_icon_from_svg(svg, color)
    
    @staticmethod
    def file_icon(color: str = "#E4E4E7") -> QtGui.QIcon:
        """Иконка файла."""
        svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M13 2H6C4.89543 2 4 2.89543 4 4V20C4 21.1046 4.89543 22 6 22H18C19.1046 22 20 21.1046 20 20V9L13 2Z" 
                  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M13 2V9H20" 
                  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        return CustomIcons.create_icon_from_svg(svg, color)
    
    @staticmethod
    def folder_icon(color: str = "#E4E4E7") -> QtGui.QIcon:
        """Иконка папки."""
        svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M22 19C22 20.1046 21.1046 21 20 21H4C2.89543 21 2 20.1046 2 19V5C2 3.89543 2.89543 3 4 3H9L11 6H20C21.1046 6 22 6.89543 22 7V19Z" 
                  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        return CustomIcons.create_icon_from_svg(svg, color)
    
    @staticmethod
    def chart_icon(color: str = "#E4E4E7") -> QtGui.QIcon:
        """Иконка графика."""
        svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="3" y="10" width="4" height="11" stroke="currentColor" stroke-width="2"/>
            <rect x="10" y="6" width="4" height="15" stroke="currentColor" stroke-width="2"/>
            <rect x="17" y="3" width="4" height="18" stroke="currentColor" stroke-width="2"/>
        </svg>'''
        return CustomIcons.create_icon_from_svg(svg, color)
    
    @staticmethod
    def list_icon(color: str = "#E4E4E7") -> QtGui.QIcon:
        """Иконка списка."""
        svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <line x1="8" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="8" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="8" y1="18" x2="21" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <circle cx="3" cy="6" r="1" fill="currentColor"/>
            <circle cx="3" cy="12" r="1" fill="currentColor"/>
            <circle cx="3" cy="18" r="1" fill="currentColor"/>
        </svg>'''
        return CustomIcons.create_icon_from_svg(svg, color)
    
    @staticmethod
    def calendar_icon(color: str = "#E4E4E7") -> QtGui.QIcon:
        """Иконка календаря."""
        svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
            <line x1="16" y1="2" x2="16" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="8" y1="2" x2="8" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="3" y1="10" x2="21" y2="10" stroke="currentColor" stroke-width="2"/>
        </svg>'''
        return CustomIcons.create_icon_from_svg(svg, color)
    
    @staticmethod
    def delete_icon(color: str = "#E4E4E7") -> QtGui.QIcon:
        """Иконка удаления."""
        svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 6H5H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M8 6V4C8 3.44772 8.44772 3 9 3H15C15.5523 3 16 3.44772 16 4V6M19 6V20C19 20.5523 18.5523 21 18 21H6C5.44772 21 5 20.5523 5 20V6H19Z" 
                  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M10 11V17M14 11V17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        return CustomIcons.create_icon_from_svg(svg, color)
    
    @staticmethod
    def plus_icon(color: str = "#E4E4E7") -> QtGui.QIcon:
        """Иконка плюса."""
        svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 5V19M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        return CustomIcons.create_icon_from_svg(svg, color)

    @staticmethod
    def screenshot_icon(color: str = "#E4E4E7") -> QtGui.QIcon:
        """Иконка скриншота."""
        svg = '''<svg viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path fill="currentColor" d="M6,19V17c0-0.552-0.448-1-1-1H5c-0.552,0-1,0.448-1,1V19c0,0.552,0.448,1,1,1H5C5.552,20,6,19.552,6,19z"/>
            <path fill="currentColor" d="M10,5L10,5c0,0.553,0.448,1,1,1H13c0.552,0,1-0.448,1-1V5c0-0.552-0.448-1-1-1H11C10.448,4,10,4.448,10,5z"/>
            <path fill="currentColor" d="M5,14L5,14c0.553,0,1-0.448,1-1V11c0-0.552-0.448-1-1-1H5c-0.552,0-1,0.448-1,1V13C4,13.552,4.448,14,5,14z"/>
            <path fill="currentColor" d="M23,6h1l0,1c0,0.552,0.448,1,1,1h0c0.552,0,1-0.448,1-1V6c0-1.105-0.895-2-2-2h-1c-0.552,0-1,0.448-1,1v0C22,5.552,22.448,6,23,6z"/>
            <path fill="currentColor" d="M16,5L16,5c0,0.552,0.448,1,1,1h2c0.552,0,1-0.448,1-1v0c0-0.552-0.448-1-1-1h-2C16.448,4,16,4.448,16,5z"/>
            <path fill="currentColor" d="M7,24H6v-1c0-0.552-0.448-1-1-1H5c-0.552,0-1,0.448-1,1v1c0,1.105,0.895,2,2,2h1c0.552,0,1-0.448,1-1V25C8,24.448,7.552,24,7,24z"/>
            <path fill="currentColor" d="M6,7V6h1c0.552,0,1-0.448,1-1V5c0-0.552-0.448-1-1-1H6C4.895,4,4,4.895,4,6v1c0,0.552,0.448,1,1,1H5C5.552,8,6,7.552,6,7z"/>
            <path fill="currentColor" d="M24,11l0,2.001c0,0.552,0.448,1,1,1h0c0.552,0,1-0.448,1-1V11c0-0.552-0.448-1-1-1h0C24.448,10,24,10.448,24,11z"/>
            <path fill="currentColor" d="M25,16h-1.764c-0.758,0-1.45-0.428-1.789-1.106l-0.171-0.342C21.107,14.214,20.761,14,20.382,14h-4.764c-0.379,0-0.725,0.214-0.894,0.553l-0.171,0.342C14.214,15.572,13.521,16,12.764,16H11c-0.552,0-1,0.448-1,1v8c0,0.552,0.448,1,1,1h14c0.552,0,1-0.448,1-1v-8C26,16.448,25.552,16,25,16z M18,25c-2.209,0-4-1.791-4-4c0-2.209,1.791-4,4-4s4,1.791,4,4C22,23.209,20.209,25,18,25z"/>
            <circle fill="currentColor" cx="18" cy="21" r="2"/>
        </svg>'''
        return CustomIcons.create_icon_from_svg(svg, color)
