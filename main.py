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
        self.settings_window = SettingsWindow(config_path)
        self.overlay = SubtitleOverlay(
            font_size=self.config['subtitle']['font_size'],
            font_color=self.config['subtitle']['font_color']
        )
        
        # Engines
        self.vad = VADEngine(threshold=self.config['asr']['vad_threshold'])
        self.asr = ASREngine()
        self.translator = Translator(
            provider=self.config['translation_provider'],
            api_key=self.config['api_keys'].get(self.config['translation_provider']),
            target_lang=self.config['target_language']
        )
        
        # Audio
        self.capture = AudioCapture()
        
        # Connections
        self.settings_window.start_btn.clicked.connect(self.start_system)
        
    def start_system(self):
        if self.running:
            return
            
        self.settings_window.start_btn.setEnabled(False)
        self.settings_window.start_btn.setText("正在啟動 ASR...")
        
        # Run ASR loading in a thread to keep UI responsive
        threading.Thread(target=self._initialize_and_run, daemon=True).start()

    def _initialize_and_run(self):
        try:
            # 1. Load ASR
            self.asr.load(
                model_dir=self.config['asr']['model_dir'],
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
        import librosa
        
        speech_buffer = []
        silence_count = 0
        max_silence = 25 # ~1.5s silence, better for continuous speech
        
        raw_buffer = [] # Buffer for incoming raw chunks
        processed_16k_buffer = np.array([], dtype=np.float32)
        
        target_sr = 16000
        
        while self.running:
            chunk_data = self.capture.get_audio_chunk()
            if chunk_data is None:
                await asyncio.sleep(0.01)
                continue
                
            # 1. Convert to float32 mono at native rate
            native_rate = self.capture.actual_rate
            channels = self.capture.channels
            
            audio_native = np.frombuffer(chunk_data, dtype=np.int16).astype(np.float32) / 32768.0
            if channels > 1:
                audio_native = audio_native.reshape(-1, channels).mean(axis=1)
            
            # 2. Resample to 16kHz
            if native_rate != target_sr:
                audio_16k = librosa.resample(audio_native, orig_sr=native_rate, target_sr=target_sr)
            else:
                audio_16k = audio_native
                
            # 3. Add to processed buffer
            processed_16k_buffer = np.concatenate([processed_16k_buffer, audio_16k])
            
            # 4. Extract 512-sample chunks for VAD
            while len(processed_16k_buffer) >= 512:
                vad_chunk = processed_16k_buffer[:512]
                processed_16k_buffer = processed_16k_buffer[512:]
                
                is_speech, prob = self.vad.is_speech(vad_chunk)
                
                if is_speech:
                    if not speech_buffer:
                        print(f"\nSpeech started (prob: {prob:.2f})")
                    speech_buffer.append(vad_chunk)
                    silence_count = 0
                else:
                    if speech_buffer:
                        silence_count += 1
                        speech_buffer.append(vad_chunk)
                        
                        if silence_count % 5 == 0:
                            print("s", end="", flush=True)
                            
                        # If silence long enough OR buffer too long
                        if silence_count >= max_silence or len(speech_buffer) > 800:
                            segment = np.concatenate(speech_buffer)
                            speech_buffer = []
                            silence_count = 0
                            
                            print(f"\nSegment detected, len: {len(segment)/16000:.2f}s")
                            import soundfile as sf
                            sf.write("debug_capture.wav", segment, 16000)
                            asyncio.create_task(self.transcribe_and_translate(segment))
                        
    async def transcribe_and_translate(self, audio):
        try:
            # 1. ASR - Pass language hint for better quality
            lang_hint = "Japanese" if self.config.get('source_language') == "ja" else None
            print("Transcribing...")
            text = await asyncio.to_thread(self.asr.transcribe, audio, language=lang_hint)
            if not text:
                print("ASR returned empty text.")
                return
                
            print(f"ASR: {text}")
            
            # 2. Translate
            translated = await self.translator.translate(text, source_lang=self.config['source_language'])
            print(f"TRN: {translated}")
            
            # 3. Update Overlay (Thread-safe via Signal)
            self.overlay.text_updated.emit(text, translated)
            
        except Exception as e:
            print(f"Processing error: {e}")

    def run(self):
        self.settings_window.show()
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = TranslatorApp()
    app.run()
