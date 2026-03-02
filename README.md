# Live Subtitle Translator

This is a Python-based real-time speech recognition and translation tool, designed to intercept computer system audio (Loopback) and generate bilingual subtitles on the fly.

## 🌟 Features

- **System Audio Capture**: Directly intercepts speaker output, allowing you to capture sound from videos, games, or live streams without needing a microphone.
- **Dual-Engine ASR Recognition**:
  - **CPU Mode (OpenVINO)**: Lightweight, does not require a dedicated GPU, suitable for standard desktop/laptop computers.
  - **CUDA Mode (faster-whisper / CTranslate2)**: Automatically utilizes NVIDIA GPU computing power for ultra-low latency, and supports switching between multiple graphics cards.
- **Real-time Translation**: Supports Google (Free/API), DeepL, and Gemini API translation.
- **Transparent Overlay**: Frameless, fully transparent subtitle display with click-through support, ensuring it doesn't interfere with your operations.
- **Environment Automation**: Uses `uv` for environment management, enabling one-click startup.

## 🛠️ Quick Start

### 1. Prerequisites
Ensure your computer has [uv](https://github.com/astral-sh/uv) installed.

### 2. Environment Setup (including NVIDIA CUDA support)
If you are using this for the first time, or just deleted the `.venv` environment, please execute the following steps:

```powershell
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```
*(We use `uv` for dependency management. GPU mode requires `nvidia-cublas-cu12` which is included in `requirements.txt`.)*

### 3. Download Model Weights
Before running for the first time, it is highly recommended to double-click and execute `setup_models.bat` to pre-download the required model files.
An interactive menu will pop up during execution, allowing you to choose freely:
- **[1] Default Recommendation: Download GPU Model (faster-whisper)** (approx. 3 GB), for NVIDIA graphics cards.
- **[2] Download CPU Model (OpenVINO)** (approx. 1.2 GB), for Intel/general CPU usage.
- **[3] Download Both**.

*(If you skip this step, the GPU mode will get stuck downloading in the background via the command line the first time you start the main program.)*


### 4. System and Configuration (`config.yaml`)
Before or during runtime, you can open and edit the `config.yaml` file in the project root directory to customize behaviors:

#### **ASR Inference and Segmentation Control**
- **asr.device**: Switch the inference engine
  - `CPU`: Use OpenVINO mode.
  - `CUDA`: Use NVIDIA GPU mode (faster-whisper / CTranslate2).
  - `CUDA:X`: (e.g., `CUDA:0`) Specify a particular NVIDIA graphics card.
- **asr.vad_threshold**: Voice detection sensitivity (default `0.3`).
  - **Lower value**: More sensitive, can capture faint human voices.
  - **Higher value**: Stricter, filters out background noise.
- **asr.max_silence_seconds**: Speech segmentation threshold (default `0.5`).
  - If speech pauses exceed this number of seconds, the sentence is considered finished and sent for translation.
  - Setting it too short will cause sentences to be chopped up; setting it too long will slow down subtitle popup.
- **asr.max_segment_seconds**: Maximum seconds per single sentence (default `10.0`).
  - When this duration is reached, it will forcefully segment the speech even if there is no silence, preventing recognition lag caused by overly long sentences.

#### **Subtitle Format Control (Subtitle)**
- **subtitle.font_size**: Font size of the translated text (the original text will automatically adjust to a slightly smaller size).
- **subtitle.history_size**: Number of subtitle lines displayed simultaneously (default `3`), new subtitles will push up older ones.
- **subtitle.line_spacing**: Vertical spacing between each set of bilingual subtitles.
- **subtitle.display_duration**: Number of seconds the subtitle remains displayed after no voice updates (default `10`).
- **subtitle.bg_opacity**: Transparency of the background semi-transparent black overlay (`0.0`~`1.0`).

#### **Other Core Settings**
- **source_language**: Source audio language (default `ja` for Japanese).
- **translation_provider**: Translation service provider (default `google_free`).
- **target_language**: Target translation language (default `zh-TW`).

*(You can also directly change the translation provider and language through the GUI window)*

### 5. Start the System
Double-click `start.bat` or run:
```powershell
./start.bat
```

## 📂 Project Structure
- `main.py`: System entry point.
- `src/`: Core logic modules (audio, ASR, translation, UI).
- `config.yaml`: System persistence settings.
- `download_models.py`: Model download utility.

## 📜 Credits & Acknowledgments

This project is built upon the following amazing open-source projects and services:

- **ASR Model (GPU)**: [Whisper large-v3](https://huggingface.co/Systran/faster-whisper-large-v3) by OpenAI, served via **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** (CTranslate2).
- **ASR Model (CPU)**: [Qwen3-ASR-0.6B](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) by Alibaba Qwen Team, quantized to INT8 via OpenVINO.
- **VAD Model**: [Silero VAD](https://github.com/snakers4/silero-vad) by Silero.
- **Inference Engines**: [OpenVINO™ toolkit](https://github.com/openvinotoolkit/openvino) (Intel, for CPU mode) and [CTranslate2](https://github.com/OpenNMT/CTranslate2) (for GPU mode).
- **Translation Services**: Google Translate, [DeepL](https://www.deepl.com/), and [Google Gemini](https://ai.google.dev/).
- **GUI Framework**: [PySide6](https://pypi.org/project/PySide6/) (Qt for Python).
- **Package Management**: [uv](https://github.com/astral-sh/uv) by Astral.

---

Developed with ❤️ for real-time accessibility.
