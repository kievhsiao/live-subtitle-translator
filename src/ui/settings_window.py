import sys
import yaml
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QComboBox, QPushButton, QFormLayout, QGroupBox,
    QDoubleSpinBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal

class SettingsWindow(QMainWindow):
    """Main dashboard for configuration and control."""
    settings_saved = Signal(dict)
    
    def __init__(self, config_path="config.yaml", config=None):
        super().__init__()
        self.config_path = config_path
        if config is not None:
            self.config = config
        else:
            self._load_config()
        
        self.setWindowTitle("即時翻譯字幕系統 - 設定")
        self.resize(550, 750) # 增大容量
        
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

    def save_config(self):
        """Gather all UI values, save to file, and emit signal."""
        # Update API Keys
        self.config['api_keys']['google'] = self.google_key.text()
        self.config['api_keys']['deepl'] = self.deepl_key.text()
        self.config['api_keys']['gemini'] = self.gemini_key.text()
        
        # Update General
        self.config['translation_provider'] = self.provider_combo.currentText()
        self.config['target_language'] = self.target_lang_combo.currentText()
        self.config['source_language'] = self.source_lang_combo.currentText()
        
        # Update ASR
        self.config['asr']['device'] = self.device_combo.currentText()
        self.config['asr']['vad_threshold'] = self.vad_threshold.value()
        self.config['asr']['max_silence_seconds'] = self.max_silence.value()
        self.config['asr']['max_segment_seconds'] = self.max_segment.value()
        
        # Update Subtitle
        self.config['subtitle']['font_size'] = self.font_size.value()
        self.config['subtitle']['history_size'] = self.history_size.value()
        self.config['subtitle']['line_spacing'] = self.line_spacing.value()
        self.config['subtitle']['display_duration'] = self.display_duration.value()
        self.config['subtitle']['bg_opacity'] = self.bg_opacity.value()

        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f)
            
        print("Settings saved.")
        self.settings_saved.emit(self.config)
        # self.close()  <-- 移除此行，防止程式關閉

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
        pref_group = QGroupBox("翻譯與語系")
        pref_form = QFormLayout(pref_group)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["google_free", "google", "deepl", "gemini"])
        self.provider_combo.setCurrentText(self.config.get('translation_provider', 'google_free'))
        
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(["ja", "en", "ko", "zh-TW"])
        self.source_lang_combo.setCurrentText(self.config.get('source_language', 'ja'))
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(["zh-TW", "zh-CN", "ja", "ko", "en"])
        self.target_lang_combo.setCurrentText(self.config.get('target_language', 'zh-TW'))
        
        pref_form.addRow("翻譯服務:", self.provider_combo)
        pref_form.addRow("來源語音:", self.source_lang_combo)
        pref_form.addRow("目標語言:", self.target_lang_combo)
        
        self.layout.addWidget(pref_group)
        
        # ASR & Device Settings
        asr_group = QGroupBox("ASR 辨識與分段控制")
        asr_form = QFormLayout(asr_group)
        
        self.device_combo = QComboBox()
        self.device_combo.addItems(["CPU", "CUDA", "CUDA:0", "CUDA:1"])
        self.device_combo.setEditable(True)
        self.device_combo.setCurrentText(self.config.get('asr', {}).get('device', 'CPU'))
        
        self.vad_threshold = QDoubleSpinBox()
        self.vad_threshold.setRange(0.1, 0.9)
        self.vad_threshold.setSingleStep(0.05)
        self.vad_threshold.setValue(self.config.get('asr', {}).get('vad_threshold', 0.4))
        
        self.max_silence = QDoubleSpinBox()
        self.max_silence.setRange(0.1, 5.0)
        self.max_silence.setSingleStep(0.1)
        self.max_silence.setValue(self.config.get('asr', {}).get('max_silence_seconds', 0.5))
        
        self.max_segment = QDoubleSpinBox()
        self.max_segment.setRange(1.0, 30.0)
        self.max_segment.setValue(self.config.get('asr', {}).get('max_segment_seconds', 10.0))
        
        asr_form.addRow("推論裝置 (Device):", self.device_combo)
        asr_form.addRow("VAD 靈敏度:", self.vad_threshold)
        asr_form.addRow("靜音切分秒數:", self.max_silence)
        asr_form.addRow("最長強制切分秒數:", self.max_segment)
        
        self.layout.addWidget(asr_group)
        
        # Subtitle Appearance
        sub_group = QGroupBox("字幕外觀與顯示")
        sub_form = QFormLayout(sub_group)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(12, 72)
        self.font_size.setValue(self.config.get('subtitle', {}).get('font_size', 24))
        
        self.history_size = QSpinBox()
        self.history_size.setRange(1, 10)
        self.history_size.setValue(self.config.get('subtitle', {}).get('history_size', 3))
        
        self.line_spacing = QSpinBox()
        self.line_spacing.setRange(0, 100)
        self.line_spacing.setValue(self.config.get('subtitle', {}).get('line_spacing', 15))
        
        self.display_duration = QSpinBox()
        self.display_duration.setRange(1, 60)
        self.display_duration.setValue(self.config.get('subtitle', {}).get('display_duration', 10))
        
        self.bg_opacity = QDoubleSpinBox()
        self.bg_opacity.setRange(0.0, 1.0)
        self.bg_opacity.setSingleStep(0.1)
        self.bg_opacity.setValue(self.config.get('subtitle', {}).get('bg_opacity', 0.4))
        
        sub_form.addRow("字體大小:", self.font_size)
        sub_form.addRow("歷史顯示行數:", self.history_size)
        sub_form.addRow("行距 (間隔):", self.line_spacing)
        sub_form.addRow("字幕逗留秒數:", self.display_duration)
        sub_form.addRow("背景透明度 (0-1):", self.bg_opacity)
        
        self.layout.addWidget(sub_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("啟動系統")
        self.start_btn.setStyleSheet("background-color: #2e7d32; color: white; height: 40px; font-weight: bold;")
        
        self.save_btn = QPushButton("儲存設定")
        self.save_btn.clicked.connect(self.save_config)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.start_btn)
        self.layout.addLayout(btn_layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())
