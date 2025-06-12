from PyQt6 import QtWidgets, QtGui, QtCore

class GradientLabel(QtWidgets.QLabel):
    """QLabel с поддержкой градиентного текста."""

    def __init__(self, text: str = "", parent: QtWidgets.QWidget | None = None):
        super().__init__(text, parent)
        self.colors = [QtGui.QColor("#FFD700"), QtGui.QColor("#FFA500")]

    def setColors(self, colors: list[str]) -> None:
        """Устанавливает цвета градиента."""
        self.colors = [QtGui.QColor(c) for c in colors]
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        # Рисуем текст с градиентом
        painter = QtGui.QPainter(self)
        gradient = QtGui.QLinearGradient(0, 0, self.width(), 0)
        if len(self.colors) == 1:
            gradient.setColorAt(0, self.colors[0])
            gradient.setColorAt(1, self.colors[0])
        else:
            step = 1 / (len(self.colors) - 1)
            for i, color in enumerate(self.colors):
                gradient.setColorAt(i * step, color)
        painter.setPen(QtGui.QPen(QtGui.QBrush(gradient), 0))
        painter.setFont(self.font())
        painter.drawText(self.rect(), int(self.alignment() or QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter), self.text())

