import sys
import yaml
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QComboBox, QPushButton, QFormLayout, QGroupBox
)
from PySide6.QtCore import Qt

class SettingsWindow(QMainWindow):
    """Main dashboard for configuration and control."""
    
    def __init__(self, config_path="config.yaml"):
        super().__init__()
        self.config_path = config_path
        self._load_config()
        
        self.setWindowTitle("即時翻譯字幕系統 - 設定")
        self.resize(500, 450)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self._build_ui()

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception:
            self.config = {}

    def _save_config(self):
        # Update config with UI values
        self.config['api_keys']['google'] = self.google_key.text()
        self.config['api_keys']['deepl'] = self.deepl_key.text()
        self.config['api_keys']['gemini'] = self.gemini_key.text()
        self.config['translation_provider'] = self.provider_combo.currentText()
        self.config['target_language'] = self.target_lang_combo.currentText()
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f)
        print("Settings saved.")
        self.close()

    def _build_ui(self):
        # API Keys Group
        api_group = QGroupBox("API 設定")
        api_form = QFormLayout(api_group)
        
        self.google_key = QLineEdit(self.config.get('api_keys', {}).get('google', ''))
        self.deepl_key = QLineEdit(self.config.get('api_keys', {}).get('deepl', ''))
        self.gemini_key = QLineEdit(self.config.get('api_keys', {}).get('gemini', ''))
        
        api_form.addRow("Google Translation API Key:", self.google_key)
        api_form.addRow("DeepL API Key:", self.deepl_key)
        api_form.addRow("Gemini API Key:", self.gemini_key)
        
        self.layout.addWidget(api_group)
        
        # Translation Settings
        pref_group = QGroupBox("翻譯偏好")
        pref_form = QFormLayout(pref_group)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["google_free", "google", "deepl", "gemini"])
        self.provider_combo.setCurrentText(self.config.get('translation_provider', 'google_free'))
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(["zh-TW", "zh-CN", "ja", "ko", "en"])
        self.target_lang_combo.setCurrentText(self.config.get('target_language', 'zh-TW'))
        
        pref_form.addRow("翻譯服務供應商:", self.provider_combo)
        pref_form.addRow("目標語言:", self.target_lang_combo)
        
        self.layout.addWidget(pref_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("啟動系統")
        self.start_btn.setStyleSheet("background-color: #2e7d32; color: white; height: 40px; font-weight: bold;")
        
        self.save_btn = QPushButton("儲存設定")
        self.save_btn.clicked.connect(self._save_config)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.start_btn)
        self.layout.addLayout(btn_layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())
