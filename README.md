# 即時翻譯字幕系統 (Live Subtitle Translator)

這是一個基於 Python 的即時語音辨識與翻譯工具，專為攔截電腦系統音訊 (Loopback) 並即時產生雙語字幕而設計。

## 🌟 特色

- **系統音擷取**：直接攔截揚聲器輸出，無需麥克風即可擷取影片、遊戲或直播音訊。
- **雙引擎 ASR 辨識**：
  - **CPU 模式 (OpenVINO)**：輕量、免安裝大顯卡，適合一般文書機。
  - **CUDA 模式 (PyTorch)**：自動調用 NVIDIA 顯卡算力，極低延遲，並支援多顯卡切換。
- **即時翻譯**：支援 Google (免費版/API)、DeepL 及 Gemini API 翻譯。
- **透明 Overlay**：無邊框全透明字幕顯示，支援點擊穿透，不干擾操作。
- **環境自動化**：使用 `uv` 管理環境，一鍵啟動。

## 🛠️ 快速開始

### 1. 環境準備
請確保您的電腦已安裝 [uv](https://github.com/astral-sh/uv)。

### 2. 環境安裝 (包含 NVIDIA CUDA 支援)
如果您是第一次使用，或剛刪除了 `.venv` 環境，請執行以下步驟：

```powershell
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```
*(我們特別於 requirements.txt 內指明了 PyTorch CUDA 12.4 下載位置，以確保支援 GPU 雙引擎。)*

### 3. 下載模型權重
第一次執行前，強烈建議您按兩下執行 `setup_models.bat` 來預先下載所需的模型檔案。
執行時會跳出互動式選單，您可以自由選擇：
- **[1] 預設推薦：下載 GPU 模型 (PyTorch)**（約 2.3 GB），供 NVIDIA 顯卡使用。
- **[2] 下載 CPU 模型 (OpenVINO)**（約 1.2 GB），供 Intel/一般 CPU 使用。
- **[3] 兩者皆下載**。

*(若您跳過此步，GPU 模式會在您第一次啟動主程式時卡在命令列進行背景下載。)*


### 4. 系統與顯卡配置 (config.yaml)
在啟動程式前或執行時，您可以開啟並編輯專案根目錄下的 `config.yaml` 來自訂行為：

#### **ASR 推理與分段控制**
- **asr.device**: 切換推理引擎
  - `CPU`: 使用 OpenVINO 模式。
  - `CUDA`: 使用 NVIDIA GPU PyTorch 模式。
  - `CUDA:X`: (例如: `CUDA:0`) 指定特定的 NVIDIA 顯卡。
- **asr.max_silence_seconds**: 語音切分門檻。靜音超過此秒數即送出辨識 (預設 `0.5`)。
- **asr.max_segment_seconds**: 單句最長秒數。達到此秒數即強行切分，防止延遲 (預設 `10.0`)。

#### **字幕格式控制 (Subtitle)**
- **subtitle.font_size**: 翻譯文字的字體大小 (原文會自動調整為稍小字體)。
- **subtitle.history_size**: 同時顯示的字幕行數 (預設 `3`)，新字幕會推擠舊字幕。
- **subtitle.line_spacing**: 每組雙語字幕之間的垂直間距。
- **subtitle.display_duration**: 字幕在無語音更新後，持續顯示的秒數 (預設 `10`)。
- **subtitle.bg_opacity**: 背景半透明黑框的透明度 (`0.0`~`1.0`)。

#### **其他核心設定**
- **source_language**: 來源語音 (預設為 `ja` 日文)
- **translation_provider**: 翻譯供應商 (預設為 `google_free`)
- **target_language**: 目標語言 (預設為 `zh-TW`)

*(您也可以直接透過 GUI 視窗更改翻譯供應商與語系)*

### 5. 啟動系統
連按兩下 `start.bat` 或執行：
```powershell
./start.bat
```

## 📂 專案結構
- `main.py`: 系統進入點。
- `src/`: 核心邏輯模組 (音訊、ASR、翻譯、UI)。
- `config.yaml`: 系統持久化設定。
- `download_models.py`: 模型下載公用程式。

## ⚠️ 注意事項
- **首次執行**：下載模型需要一定時間，請保持網路暢通。
- **缺少 CPU 模型**：若執行 ASR 報錯，請確認 `models/cpu/qwen3_asr_int8` 目錄與 `mel_filters.npy` 檔案完整。

---
Developed with ❤️ for real-time accessibility.
