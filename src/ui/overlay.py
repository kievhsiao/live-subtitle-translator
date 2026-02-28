import sys
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QGraphicsDropShadowEffect, QSizeGrip
from PySide6.QtCore import Qt, QTimer, QPoint, QRect, Signal, Slot
from PySide6.QtGui import QFont, QColor

class SubtitleOverlay(QMainWindow):
    """Transparent, frameless overlay window for subtitles with history support."""
    text_updated = Signal(str, str)
    text_updated_with_id = Signal(str, str, str) # original, translated, uid
    
    def __init__(self, font_size=24, font_color="#FFFFFF", bg_opacity=0.4, 
                 history_size=3, line_spacing=10, display_duration=5):
        super().__init__()
        self.text_updated.connect(self.update_text)
        self.text_updated_with_id.connect(self.update_text)
        
        self.history_size = history_size
        self.line_spacing = line_spacing
        self.display_duration = display_duration
        self.font_size = font_size
        self.font_color = font_color
        self.history = [] # List of dict
        self._dragging = False
        self._drag_pos = QPoint()
        
        self.setWindowFlags(
            Qt.FramelessWindowHint |    # 無邊框以支援透明
            Qt.WindowStaysOnTopHint |
            Qt.Tool                     # 不要在工作列顯示
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("即時字幕視窗")
        
        # Central Widget & Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 為了避免套用的 style 汙染到子元件 (如 QLabel / 容器)，指派一個 ObjectName 給中央元件
        self.central_widget.setObjectName("bgWidget")
        
        # 套用背景顏色與透明度，使用更穩定的 QSS 語法，避免 rgba 小數點解析錯誤
        bg_val = int(bg_opacity * 255)
        self.central_widget.setStyleSheet(
            f"#bgWidget {{ "
            f"background-color: rgba(0, 0, 0, {bg_val}); "
            f"border: 1px solid rgba(255, 255, 255, 30); "
            f"border-radius: 5px; "
            f"}}"
        )
        
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(30, 15, 30, 15)
        self.layout.setAlignment(Qt.AlignBottom)
        self.layout.setSpacing(self.line_spacing)
        
        # 加入右下角縮放控制塊
        self.sizegrip = QSizeGrip(self.central_widget)
        self.sizegrip.setStyleSheet("background: transparent;")
        self.sizegrip.setFixedSize(20, 20)
        
        # Initial position
        screen = QApplication.primaryScreen().geometry()
        w = int(screen.width() * 0.85)
        h = int(screen.height() * 0.3)
        self.resize(w, h)
        self.setMinimumSize(400, 100) # 寬度可以更小一點點
        self.move((screen.width() - w) // 2, screen.height() - h - 100)

    def resizeEvent(self, event):
        """保持 SizeGrip 在右下角"""
        super().resizeEvent(event)
        self.sizegrip.move(self.width() - self.sizegrip.width(), 
                           self.height() - self.sizegrip.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def apply_settings(self, font_size=None, font_color=None, bg_opacity=None, 
                       history_size=None, line_spacing=None, display_duration=None):
        """Update overlay settings on the fly."""
        if font_size is not None: self.font_size = font_size
        if font_color is not None: self.font_color = font_color
        if bg_opacity is not None:
             bg_val = int(bg_opacity * 255)
             self.central_widget.setStyleSheet(
                 f"#bgWidget {{ "
                 f"background-color: rgba(0, 0, 0, {bg_val}); "
                 f"border: 1px solid rgba(255, 255, 255, 30); "
                 f"border-radius: 5px; "
                 f"}}"
             )
        if history_size is not None: self.history_size = history_size
        if line_spacing is not None: 
            self.line_spacing = line_spacing
            self.layout.setSpacing(self.line_spacing)
        if display_duration is not None: self.display_duration = display_duration
        
        # 立即重繪現有歷史 (如果有)
        if self.history:
            self.refresh_display()

    def refresh_display(self):
        """Redraw all history items with current settings."""
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        for i, item in enumerate(self.history):
            item_widget = self._create_item_widget(item['original'], item['translated'])
            self.layout.addWidget(item_widget)

    def _create_item_widget(self, original, translated):
        """Create a widget containing one pair of subtitles."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 5, 0, 5) # 移除左右 margin，讓文字有最大空間
        layout.setSpacing(5) # 原文與譯文之間的微小間距
        
        orig_label = QLabel(original)
        self._setup_label(orig_label, self.font_size - 6, self.font_color, opacity=0.8)
        
        trans_label = QLabel(translated)
        self._setup_label(trans_label, self.font_size, self.font_color, bold=True)
        
        layout.addWidget(orig_label)
        layout.addWidget(trans_label)
        return container

    def _setup_label(self, label, font_size, color, bold=False, opacity=1.0):
        font = QFont("Microsoft JhengHei", font_size)
        if bold:
            font.setBold(True)
        label.setFont(font)
        
        # 使用 RGBA 色碼實作透明度 (給原文用)，並確保沒有繼承到邊框或背景
        alpha = int(opacity * 255)
        if opacity < 1.0:
            label.setStyleSheet(f"QLabel {{ color: rgba(255, 255, 255, {alpha}); background-color: transparent; border: none; }}")
        else:
            # 確保十六進位顏色正確套用
            label.setStyleSheet(f"QLabel {{ color: {color}; background-color: transparent; border: none; }}")
            
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        # 強制標籤可以橫向擴張
        from PySide6.QtWidgets import QSizePolicy
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # 加入文字陰影，增強高級感與可讀性
        shadow = QGraphicsDropShadowEffect(label)
        shadow.setBlurRadius(5)
        shadow.setColor(QColor(0, 0, 0, 220))
        shadow.setOffset(2, 2)
        label.setGraphicsEffect(shadow)

    def update_text(self, original, translated, uid=None):
        """Add new text to history or update existing text by UID, then refresh display."""
        import uuid
        
        # 尋找是否已經有相同的 uid 在歷史紀錄中
        target_item = None
        if uid is not None:
            for item in self.history:
                if item.get('uid') == uid:
                    target_item = item
                    break
                    
        if target_item:
            # 更新現有紀錄
            if original: target_item['original'] = original
            if translated: target_item['translated'] = translated
        else:
            # 新增一筆
            uid = uid or str(uuid.uuid4())
            self.history.append({'uid': uid, 'original': original, 'translated': translated})
            if len(self.history) > self.history_size:
                self.history.pop(0)
            
        self.refresh_display()
        self.show()
        
        if hasattr(self, '_hide_timer'):
            self._hide_timer.stop()
        else:
            self._hide_timer = QTimer()
            self._hide_timer.setSingleShot(True)
            self._hide_timer.timeout.connect(self.clear_history)
            
        self._hide_timer.start(self.display_duration * 1000)
        
        return uid

    def clear_history(self):
        self.history = []
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = SubtitleOverlay()
    overlay.show()
    overlay.update_text("Hello, this is a test.", "你好，這是一個測試。")
    sys.exit(app.exec())
