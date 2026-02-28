# 即時翻譯字幕系統 (Live Subtitle Translator)

這是一個基於 Python 的即時語音辨識與翻譯工具，專為攔截電腦系統音訊 (Loopback) 並即時產生雙語字幕而設計。

## 🌟 特色

- **系統音擷取**：直接攔截揚聲器輸出，無需麥克風即可擷取影片、遊戲或直播音訊。
- **本地 ASR 辨識**：採用 **Qwen3-ASR-0.6B** 模型搭配 **OpenVINO** 加速，實現極低延遲辨識。
- **即時翻譯**：支援 Google (免費版/API)、DeepL 及 Gemini API 翻譯。
- **透明 Overlay**：無邊框全透明字幕顯示，支援點擊穿透，不干擾操作。
- **環境自動化**：使用 `uv` 管理環境，一鍵啟動。

## 🛠️ 快速開始

### 1. 環境準備
請確保您的電腦已安裝 [uv](https://github.com/astral-sh/uv)。

### 2. 下載模型權重
第一次執行前，請先執行以下指令或連按兩下 `setup_models.bat` 來下載 ASR 與 VAD 模型 (約 1.2 GB)：
```powershell
./setup_models.bat
```

### 3. 配置設定
啟動主程式後，您可以在「設定視窗」中配置：
- **翻譯供應商** (預設為 `google_free`)
- **API Key** (若使用 Gemini 或 DeepL)
- **目標語言** (預設為 `zh-TW`)

### 4. 啟動系統
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
- **缺少檔案**：若執行 ASR 報錯，請確認 `ov_models/qwen3_asr_int8` 目錄完整。

---
Developed with ❤️ for real-time accessibility.
