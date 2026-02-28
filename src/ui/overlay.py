import sys
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer, QPoint, QRect, Signal, Slot
from PySide6.QtGui import QFont, QColor

class SubtitleOverlay(QMainWindow):
    """Transparent, frameless overlay window for subtitles with history support."""
    text_updated = Signal(str, str)
    
    def __init__(self, font_size=24, font_color="#FFFFFF", bg_opacity=0.4, 
                 history_size=3, line_spacing=10, display_duration=5):
        super().__init__()
        self.text_updated.connect(self.update_text)
        
        self.history_size = history_size
        self.line_spacing = line_spacing
        self.display_duration = display_duration
        self.font_size = font_size
        self.font_color = font_color
        self.history = [] # List of (original, translated)
        
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint  # 保持置頂，但移除無邊框與穿透限制
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("即時字幕視窗")
        
        # Central Widget & Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 套用背景顏色與透明度 (RGBA)，加入細微邊框增加質感
        self.central_widget.setStyleSheet(
            f"background-color: rgba(0, 0, 0, {int(bg_opacity * 255)});"
            "border: 1px solid rgba(255, 255, 255, 0.1);"
            "border-radius: 5px;"
        )
        
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(15, 15, 15, 15) # 增加內距，視窗化後比較好看
        self.layout.setAlignment(Qt.AlignBottom | Qt.AlignCenter)
        self.layout.setSpacing(self.line_spacing) # 控制段落間距
        
        # Initial position
        screen = QApplication.primaryScreen().geometry()
        self.resize(1000, 300) # 給予一個合理的預設寬高
        self.move((screen.width() - 1000) // 2, screen.height() - 400)

    def apply_settings(self, font_size=None, font_color=None, bg_opacity=None, 
                       history_size=None, line_spacing=None, display_duration=None):
        """Update overlay settings on the fly."""
        if font_size is not None: self.font_size = font_size
        if font_color is not None: self.font_color = font_color
        if bg_opacity is not None:
             self.central_widget.setStyleSheet(f"background-color: rgba(0, 0, 0, {int(bg_opacity * 255)}); border-radius: 10px;")
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
        
        for i, (orig, trans) in enumerate(self.history):
            item_widget = self._create_item_widget(orig, trans)
            self.layout.addWidget(item_widget)

    def _create_item_widget(self, original, translated):
        """Create a widget containing one pair of subtitles."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(2) # 原文與譯文之間的微小間距
        
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
        
        # 使用 RGBA 色碼實作透明度 (給原文用)
        if opacity < 1.0:
            label.setStyleSheet(f"color: rgba(255, 255, 255, {int(opacity*255)});")
        else:
            label.setStyleSheet(f"color: {color};")
            
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)

    def update_text(self, original, translated):
        """Add new text to history and refresh display."""
        self.history.append((original, translated))
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
