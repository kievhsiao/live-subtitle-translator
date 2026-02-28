# Live Subtitle Translator 架構說明

本文件旨在說明 `live-subtitle-translator` 專案的核心架構、目錄結構、模組職責以及資料流動方式。

## 1. 系統設計概覽

這是一個專為 Windows 系統設計的「即時系統音訊擷取與雙語雙引擎翻譯」字幕工具。系統透過迴圈擷取 (Loopback) 攔截本機電腦發出的聲音，透過 VAD (語音活動偵測) 將連續音流切割成句子，並發送至 ASR (語音辨識) 引擎轉換為文字，最後透過線上 API 轉譯並顯示於置頂的透明 UI 字幕視窗上。

### 核心特色：
- **雙引擎架構 (Dual-Engine)**：
  - **CPU 模式 (OpenVINO)**：針對缺乏高階獨立顯卡的電腦進行量化優化。
  - **GPU 模式 (PyTorch/CUDA)**：提供高速且低延遲的推論，並支援切換指定的 NVIDIA 顯示卡。
- **共享資源設計**：共用的 VAD 模型與特徵過濾器被獨立存放，減少重複下載的浪費。
- **動態分段**：具備智慧靜音偵測與長句強大切分保護，實現字幕的最高即時性。

---

## 2. 目錄結構

```text
live-subtitle-translator/
├── main.py                     # 系統核心協調者與進入點
├── config.yaml                 # 使用者持久化設定檔 (裝置、語系、API Keys 等)
├── download_models.py          # 模型下載與檢查腳本
├── setup_models.bat            # 提供互動式選擇下載 (CPU/GPU) 的批次檔
├── start.bat                   # 系統啟動批次檔
├── requirements.txt            # Python 套件依賴清單 (嚴格鎖定 CUDA 12.4 版本)
│
├── models/                     # AI 模型資產目錄
│   ├── common/                 # 雙引擎共用資源 (如 mel_filters.npy 特徵過濾器)
│   ├── vad/                    # 共用語音活動偵測模型 (silero_vad_v4.onnx)
│   ├── cpu/                    # OpenVINO 專用量化權重檔 (qwen3_asr_int8)
│   └── gpu/                    # PyTorch/NVIDIA 共用原生權重庫
│       └── Qwen3-ASR-0.6B/     # 從 HuggingFace 下載的快取模型
│
└── src/                        # 核心邏輯原始碼
    ├── asr_engine.py           # 語音辨識雙引擎介面實作
    ├── vad_engine.py           # VAD 靜音與發聲邊界偵測模組
    ├── audio_capture.py        # Windows WASAPI Loopback 擷取模組
    ├── processor_numpy.py      # 音訊頻譜特徵前處理模組 (替代耗能的 transformers)
    ├── translator.py           # 翻譯 API 服務串接 (Google, DeepL, Gemini)
    └── ui/                     # 介面相關
        ├── overlay.py          # 全透明、點擊穿透的置頂字幕視窗
        └── settings_window.py  # 供使用者即時更改設定檔的 GUI 視窗
```

---

## 3. 核心類別與職責 (Modules)

### `main.TranslatorApp` (`main.py`)
- **角色**：核心調度 Orchestrator。
- **職責**：
  - 載入設定 (`config.yaml`)。
  - 初始化 VAD, ASR, Translator 與 UI 視窗。
  - 非同步啟動 `process_loop` 進行音訊擷取、緩衝與切分。
  - 管理非同步的 `transcribe_and_translate` 任務並推播至 UI 顯示。

### `src.audio_capture.WindowsAudioCapture`
- **職責**：使用 PyAudio 與 WASAPI 啟動 Loopback 麥克風，直接攔截揚聲器（喇叭）的發聲。以 Chunk 形式返回原始位元組資料。

### `src.vad_engine.VADEngine`
- **職責**：讀取 `models/vad/silero_vad_v4.onnx` 模型，將進來的 `512` 採樣點進行推論，並回報目前片段是否包含人聲 (`is_speech`)。是整個「智慧切句」機制的靈魂。

### `src.asr_engine.ASREngine`
- **職責**：擁有 `load()` 方法並對外隱藏實作細節。
  - 當設定為 `CUDA` 時：以 `local_files_only=True` 透過 `qwen_asr` 載入 PyTorch 版本的 `Qwen3-ASR-0.6B` 模型，實現極低延遲的推論。
  - 當設定為 `CPU` 時：建立專案特製的 `Processor`，讀取 `models/cpu` 下的 ONNX 編碼與解碼圖譜，交由 OpenVINO 行推論。

### `src.processor_numpy`
- **職責**：專為 CPU/OpenVINO 模式打造的特徵提取器。讀取 `models/common/mel_filters.npy`，繞過 HuggingFace Transformer 繁雜的依賴，直接使用 NumPy 高效提取音訊梅爾頻譜圖。

### `src.translator.Translator`
- **職責**：負責將 ASR 辨識出的原文（例：日文）發送至指定雲端服務，並取得翻譯文塊（例：繁體中文）。包含對應的 API 實作（Google HTTP, DeepL API, Gemini API 等）。

---

## 4. 資料流與執行流程 (Data Flow)

1. **啟動與初始化** (`start.bat` -> `main.py`)
   - 讀取 `config.yaml` 找出使用者指定的 `device` (例: `CUDA:0`) 與翻譯服務。
   - `ASREngine.load()` 根據裝置決定該載入 PyTorch 或 OpenVINO 模型。
2. **音訊擷取 (Audio Streaming)**
   - `audio_capture` 以設備原生取樣率（例如 48kHz）取得 Raw 音訊。
3. **預處理與重取樣 (Resampling)**
   - `main.py` 的音軌緩衝區 (`process_loop`) 會透過 `librosa` 將取得的音訊實時重取樣為 ASR 標準要求的 **16000 Hz** 單聲道 float32 格式。
4. **活動語音偵測 (VAD Segmentation)**
   - 取樣音軌會每隔 512 個採樣點（約 32 毫秒）送給 `vad_engine` 檢定。
   - 當發現發聲時，開始累積 `speech_buffer`。
   - 當連續靜音達到 `max_silence_seconds`，或總時長超過 `max_segment_seconds`，系統會觸發斷開條件，並建立 ASR 任務。
5. **語音辨識與翻譯 (ASR -> Translate)**
   - 將組合好的完整片段（Numpy Array）非同步送給 `asr_engine.transcribe()`。
   - 返回辨識文字後，送入 `translator.translate()` 進行二度轉換。
6. **字幕渲染 (UI Update)**
   - 使用 PySide6 Signal-Slot 機制，將取得的 `(原文, 翻譯文)` 推播回主執行緒的 `overlay.py`，更新桌面上的透明字幕畫面。
