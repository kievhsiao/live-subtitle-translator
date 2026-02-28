import sys
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer, QPoint, QRect, Signal, Slot
from PySide6.QtGui import QFont, QColor

class SubtitleOverlay(QMainWindow):
    """Transparent, frameless overlay window for subtitles."""
    text_updated = Signal(str, str) # New signal
    
    def __init__(self, font_size=24, font_color="#FFFFFF", bg_opacity=0.4):
        super().__init__()
        self.text_updated.connect(self.update_text) # Connect signal
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | # Hide from taskbar
            Qt.WindowTransparentForInput # Click through
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Central Widget & Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignCenter)
        
        # Labels for bilingual subtitles
        self.original_label = QLabel("")
        self.translated_label = QLabel("")
        
        self._setup_label(self.original_label, font_size - 4, font_color)
        self._setup_label(self.translated_label, font_size, font_color, bold=True)
        
        self.layout.addWidget(self.original_label)
        self.layout.addWidget(self.translated_label)
        
        # Initial position (Bottom 20%)
        screen = QApplication.primaryScreen().geometry()
        self.resize(screen.width() * 0.8, 120)
        self.move(screen.width() * 0.1, screen.height() * 0.8)

    def _setup_label(self, label, font_size, color, bold=False):
        font = QFont("Microsoft JhengHei", font_size)
        if bold:
            font.setBold(True)
        label.setFont(font)
        label.setStyleSheet(f"color: {color};")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)

    def update_text(self, original, translated):
        """Update subtitle text."""
        self.original_label.setText(original)
        self.translated_label.setText(translated)
        self.show()
        
        # Auto hide after 5 seconds of no update
        if hasattr(self, '_hide_timer'):
            self._hide_timer.stop()
        else:
            self._hide_timer = QTimer()
            self._hide_timer.setSingleShot(True)
            self._hide_timer.timeout.connect(self.hide_subtitles)
            
        self._hide_timer.start(5000)

    def hide_subtitles(self):
        self.original_label.setText("")
        self.translated_label.setText("")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = SubtitleOverlay()
    overlay.show()
    overlay.update_text("Hello, this is a test.", "你好，這是一個測試。")
    sys.exit(app.exec())
