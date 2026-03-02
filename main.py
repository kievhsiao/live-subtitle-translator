import sys
import threading
import queue
import time
import yaml
import asyncio
import numpy as np
from PySide6.QtWidgets import QApplication
from src.audio_capture import AudioCapture
from src.vad_engine import VADEngine
from src.asr_engine import ASREngine
from src.translator import Translator
from src.ui.overlay import SubtitleOverlay
from src.ui.settings_window import SettingsWindow

class TranslatorApp:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
            
        self.config_path = config_path
        self.running = False
        
        # UI
        self.app = QApplication(sys.argv)
        self.settings_window = SettingsWindow(config_path, config=self.config)
        self.overlay = SubtitleOverlay(
            font_size=self.config['subtitle'].get('font_size', 24),
            font_color=self.config['subtitle'].get('font_color', '#FFFFFF'),
            bg_opacity=self.config['subtitle'].get('bg_opacity', 0.4),
            history_size=self.config['subtitle'].get('history_size', 3),
            line_spacing=self.config['subtitle'].get('line_spacing', 15),
            display_duration=self.config['subtitle'].get('display_duration', 10)
        )
        
        # Engines
        self.vad = VADEngine(threshold=self.config['asr']['vad_threshold'])
        
        # 智慧判斷是否需要預載 GPU 資源
        asr_device = self.config['asr'].get('device', 'CPU').upper()
        use_gpu_preload = asr_device == 'GPU' or asr_device.startswith('CUDA')
        
        self.asr = ASREngine(use_gpu_preload=use_gpu_preload)
        self.translator = Translator(
            provider=self.config['translation_provider'],
            api_key=self.config['api_keys'].get(self.config['translation_provider']),
            target_lang=self.config['target_language']
        )
        
        # Audio
        self.capture = AudioCapture()
        
        # Connections
        self.settings_window.start_btn.clicked.connect(self.start_system)
        self.settings_window.settings_saved.connect(self.on_settings_saved)
        
    def on_settings_saved(self, new_config):
        """Handle real-time configuration updates."""
        self.config = new_config
        self.update_loop_params()
        print("Applying new configuration to running engines...")
        
        # Update Translator
        self.translator.provider = self.config['translation_provider']
        self.translator.api_key = self.config['api_keys'].get(self.config['translation_provider'])
        self.translator.target_lang = self.config['target_language']
            
        # Update VAD
        self.vad.threshold = self.config['asr'].get('vad_threshold', 0.4)
            
        # Update Overlay
        self.overlay.apply_settings(
            font_size=self.config['subtitle'].get('font_size'),
            font_color=self.config['subtitle'].get('font_color'),
            bg_opacity=self.config['subtitle'].get('bg_opacity'),
            history_size=self.config['subtitle'].get('history_size'),
            line_spacing=self.config['subtitle'].get('line_spacing'),
            display_duration=self.config['subtitle'].get('display_duration')
        )
            
    def start_system(self):
        if self.running:
            return
            
        # 點擊啟動即自動儲存與套用目前介面上的所有設定值
        self.settings_window.save_config()
        
        self.settings_window.start_btn.setEnabled(False)
        self.settings_window.start_btn.setText("正在啟動 ASR...")
        
        self.update_loop_params()
        
        # Run ASR loading in a thread to keep UI responsive
        threading.Thread(target=self._initialize_and_run, daemon=True).start()

    def update_loop_params(self):
        """Update cached parameters for the high-frequency process loop."""
        self._max_silence_chunks = int((self.config['asr'].get('max_silence_seconds', 0.5) * 16000) / 512)
        self._max_segment_chunks = int((self.config['asr'].get('max_segment_seconds', 10.0) * 16000) / 512)

    def _initialize_and_run(self):
        try:
            # 1. Load ASR
            self.asr.load(
                model_dir=self.config['asr'].get('model_dir'),
                device=self.config['asr']['device']
            )
            
            # 2. Start Capture
            self.capture.start()
            self.running = True
            
            # 3. Main processing loop
            print("Processing loop started.")
            self.settings_window.start_btn.setText("系統運行中")
            
            asyncio.run(self.process_loop())
            
        except Exception as e:
            print(f"Startup error: {e}")
            self.settings_window.start_btn.setEnabled(True)
            self.settings_window.start_btn.setText("啟動失敗，請重試")

    async def process_loop(self):
        speech_buffer = []
        silence_count = 0
        current_uid = None
        
        pending_samples = []  # list of np.ndarray chunks (取代反覆 np.concatenate)
        
        target_sr = 16000
        
        # 預計算降頻比率（啟動後取樣率不變，只需算一次）
        native_rate = self.capture.actual_rate
        channels = self.capture.channels
        downsample_ratio = native_rate / target_sr
        is_integer_ratio = (downsample_ratio == int(downsample_ratio))
        if is_integer_ratio:
            downsample_step = int(downsample_ratio)
        
        while self.running:
            # --- 延遲優化：Queue Draining (佇列抽乾) ---
            # 將目前卡在 Queue 裡面的所有聲音一次性拿出來
            chunks = []
            while True:
                chunk_data = self.capture.get_audio_chunk()
                if chunk_data is None:
                    break
                chunks.append(chunk_data)
                
            if not chunks:
                await asyncio.sleep(0.01)
                continue
                
            # 將所有細碎的 chunks 串接成一大段
            combined_chunk_data = b"".join(chunks)
                
            # 1. Convert to float32 mono at native rate
            audio_native = np.frombuffer(combined_chunk_data, dtype=np.int16).astype(np.float32) / 32768.0
            if channels > 1:
                audio_native = audio_native.reshape(-1, channels).mean(axis=1)
            
            # 2. Resample to 16kHz（取樣率分級處理，無 librosa 依賴）
            if native_rate == target_sr:
                audio_16k = audio_native
            elif is_integer_ratio:
                # 快速路徑：整數倍降頻（48kHz→16kHz, 96kHz→16kHz 等）
                audio_16k = audio_native[::downsample_step]
            else:
                # 慢速路徑：非整數倍，用 scipy（已是專案間接依賴）
                from scipy.signal import resample_poly
                from math import gcd
                g = gcd(target_sr, native_rate)
                audio_16k = resample_poly(audio_native, up=target_sr // g, down=native_rate // g).astype(np.float32)
                
            # 3. 加入 pending list（避免每次 np.concatenate）
            pending_samples.append(audio_16k)
            
            # 4. 合併一次，逐 512 送 VAD
            combined = np.concatenate(pending_samples)
            pending_samples.clear()
            
            while len(combined) >= 512:
                vad_chunk = combined[:512]
                combined = combined[512:]
                is_speech, prob = self.vad.is_speech(vad_chunk)
                
                if is_speech:
                    if not speech_buffer:
                        import uuid
                        current_uid = str(uuid.uuid4())
                        print(f"\nSpeech started (prob: {prob:.2f})")
                    speech_buffer.append(vad_chunk)
                    silence_count = 0
                else:
                    if speech_buffer:
                        silence_count += 1
                        # 只保留一部分 tail silence，避免無意義的靜音被送去辨識
                        if silence_count <= self._max_silence_chunks:
                            speech_buffer.append(vad_chunk)

                # 判斷是否達到強制出字條件 (句子太長 OR 到達靜音閥值)
                force_segment = len(speech_buffer) >= self._max_segment_chunks
                silence_segment = silence_count >= self._max_silence_chunks
                
                if speech_buffer and (force_segment or silence_segment):
                    segment = np.concatenate(speech_buffer)
                    if force_segment:
                        print(f"\n[Force Segment] segment too long, len: {len(segment)/16000:.2f}s")
                    else:
                        print(f"\nSegment detected, len: {len(segment)/16000:.2f}s")
                        
                    asyncio.create_task(self.transcribe_and_translate(segment, current_uid))
                    
                    # 狀態重置
                    speech_buffer = []
                    silence_count = 0
                    current_uid = None
            
            # 保留不足 512 的剩餘 samples
            if len(combined) > 0:
                pending_samples.append(combined)
            
            # Yield control explicitly so ASR tasks can start
            await asyncio.sleep(0)
                        
    async def transcribe_and_translate(self, audio, task_uid=None):
        try:
            import uuid
            task_uid = task_uid or str(uuid.uuid4())
            
            start_time = time.time()
            audio_duration = len(audio) / 16000.0
            print(f"\n--- [Task Start] Audio length: {audio_duration:.2f}s ---")
            
            # 1. ASR - Pass language hint for better quality
            lang_hint = "Japanese" if self.config.get('source_language') == "ja" else None
            print("Transcribing...")
            
            asr_start = time.time()
            text = await asyncio.to_thread(self.asr.transcribe, audio, language=lang_hint)
            asr_time = time.time() - asr_start
            
            if not text:
                print("ASR returned empty text.")
                return
                
            print(f"ASR [{asr_time:.2f}s]: {text}")
            
            # --- 延遲優化：漸進式渲染 (ASR 完成立刻上畫面) ---
            # 讓翻譯欄位顯示 "翻譯中..." 或留白
            self.overlay.text_updated_with_id.emit(text, "...", task_uid)
            
            # 2. Translate
            trans_start = time.time()
            translated = await self.translator.translate(text, source_lang=self.config['source_language'])
            trans_time = time.time() - trans_start
            
            print(f"TRN [{trans_time:.2f}s]: {translated}")
            
            # 3. Update Overlay (透過 UID 覆蓋翻譯內容)
            self.overlay.text_updated_with_id.emit(None, translated, task_uid)
            
            total_time = time.time() - start_time
            print(f"--- [Task End] Total latency: {total_time:.2f}s ---\n")
            
        except Exception as e:
            print(f"Processing error: {e}")

    def run(self):
        self.settings_window.show()
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = TranslatorApp()
    app.run()
