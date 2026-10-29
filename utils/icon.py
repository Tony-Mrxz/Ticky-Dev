# utils/icon.py
"""Utility module for creating application icons."""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPainterPath, QPen
from PySide6.QtCore import Qt, QPointF

import os

def load_ticky_icon():
    """Load the branded Ticky icon (ticky.ico with ticky.png fallback)."""
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for name in ("ticky.ico", "ticky.png"):
        path = os.path.join(base, name)
        if os.path.exists(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
    return create_ticky_icon()


def create_ticky_icon():
    """Create a white checkmark icon based on the Boxicons SVG design for system tray and windows."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Scale factor to convert from 24x24 SVG to 64x64 pixmap
    scale = 64.0 / 24.0
    painter.scale(scale, scale)
    
    # White color for the icon
    pen = QPen(QColor(255, 255, 255))
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Draw outer square frame (from SVG: M19 21H5c-1.1 0-2-.9-2-2V5c0-1.1.9-2 2-2h14c1.1 0 2 .9 2 2v14c0 1.1-.9 2-2 2)
    # This is a rounded rectangle from (3,3) to (21,21) with corner radius 2
    frame_path = QPainterPath()
    frame_path.addRoundedRect(3, 3, 18, 18, 2, 2)
    painter.drawPath(frame_path)
    
    # Draw checkmark (from SVG: M10.5 15.5...l-2.5-2.5L8.7 11.3l1.79 1.79 4.79-4.79 1.41 1.41-5.5 5.5...)
    # Simplified: draw the checkmark strokes
    pen.setWidth(1.5)
    painter.setPen(pen)
    
    checkmark = QPainterPath()
    # Short stroke of the check (bottom left part)
    checkmark.moveTo(7.29, 12.71)
    checkmark.lineTo(10.49, 15.91)
    # Long stroke of the check (from middle to top right)
    checkmark.lineTo(16.69, 9.71)
    
    painter.drawPath(checkmark)
    
    painter.end()
    
    return QIcon(pixmap)
