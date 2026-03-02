import os
import sys
import sysconfig
import numpy as np
import threading
from pathlib import Path

# ── Windows CUDA DLL 預先登錄 ─────────────────────────────────────────────
# ctranslate2 的原生 .pyd 在 import 時就會解析 cublas64_12.dll 等 DLL 的載入路徑。
# nvidia-cublas-cu12 等套件把 DLL 裝在 site-packages/nvidia/*/bin/，
# 需要在任何 ctranslate2 / faster_whisper import 之前呼叫 add_dll_directory 登錄。
if sys.platform == "win32":
    _nvidia_dir = os.path.join(sysconfig.get_path("purelib"), "nvidia")
    if os.path.isdir(_nvidia_dir):
        for _pkg in os.listdir(_nvidia_dir):
            _bin = os.path.join(_nvidia_dir, _pkg, "bin")
            if os.path.isdir(_bin):
                os.add_dll_directory(_bin)


# Suppress Hugging Face transformers 'temperature' warning (GenerationConfig issue)
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

from src.processor_numpy import LightProcessor


class ASREngine:
    """ASR Engine supporting OpenVINO (CPU) and faster-whisper (GPU)."""

    def __init__(self):
        self.ready = False
        self._lock = threading.Lock()

        self.is_cpu = True

        # OpenVINO resources
        self.audio_enc = None
        self.embedder = None
        self.dec_req = None
        self.processor = None
        self.pad_id = None

        # faster-whisper resources
        self.fw_model = None

    def load(self, model_dir: str | None = None, device: str = "CPU"):
        """
        Load models based on device choice.
        CUDA/GPU/CUDA:X -> faster-whisper + CTranslate2 (models/gpu)
        CPU -> OpenVINO INT8 (models/cpu)
        """
        dev_upper = device.upper()
        self.is_cpu = not (dev_upper == "GPU" or dev_upper.startswith("CUDA"))
        print(f"Loading ASR Engine targeting device: {device} (is_cpu={self.is_cpu})")

        # 自動根據模式選擇預設路徑，除非使用者有傳入特定的 model_dir
        if model_dir is None or model_dir == "" or model_dir == "ov_models" or model_dir == "models/cpu":
            if self.is_cpu:
                target_dir = "models/cpu"
            else:
                target_dir = "models/gpu/faster-whisper-large-v3"
        else:
            target_dir = model_dir

        if self.is_cpu:
            self._load_openvino(target_dir, device)
        else:
            self._load_faster_whisper(device, target_dir)

    @staticmethod
    def _add_nvidia_dll_dirs():
        """
        Windows: 讓 ctranslate2 能找到 nvidia-cublas-cu12 等套件提供的 DLL。
        這些 DLL 被安裝在 site-packages/nvidia/*/bin/ 下，需要手動以
        os.add_dll_directory() 登錄，否則 ctranslate2 的 C++ 程式庫無法載入。
        """
        import os, sys, sysconfig
        if sys.platform != "win32":
            return
        site_packages = sysconfig.get_path("purelib")
        nvidia_dir = os.path.join(site_packages, "nvidia")
        if not os.path.isdir(nvidia_dir):
            return
        for pkg in os.listdir(nvidia_dir):
            bin_dir = os.path.join(nvidia_dir, pkg, "bin")
            if os.path.isdir(bin_dir):
                os.add_dll_directory(bin_dir)
                print(f"[DLL] Added: {bin_dir}")

    def _load_faster_whisper(self, requested_device: str, local_model_dir_str: str):

        local_model_dir = Path(local_model_dir_str)
        print(f"Loading faster-whisper ASR model from ({local_model_dir})...")

        # Windows: 先登錄 nvidia-*-cu12 套件的 DLL 目錄，讓 ctranslate2 能找到 cublas64_12.dll 等
        self._add_nvidia_dll_dirs()

        from faster_whisper import WhisperModel

        # 解析 GPU index（例如 CUDA:1 → device_index=1）
        gpu_index = 0
        if ":" in requested_device:
            try:
                gpu_index = int(requested_device.split(":")[1])
            except (ValueError, IndexError):
                gpu_index = 0

        try:
            # 若本地路徑存在，使用本地模型；否則以模型名稱自動下載
            if local_model_dir.exists():
                model_path = str(local_model_dir)
            else:
                print(f"Local model not found at {local_model_dir}. Will auto-download 'large-v3'...")
                model_path = "large-v3"

            self.fw_model = WhisperModel(
                model_path,
                device="cuda",
                device_index=gpu_index,
                compute_type="int8_float16",  # float16 requires cublas64_12.dll; int8_float16 uses cuDNN (already available)
                local_files_only=local_model_dir.exists(),
            )
            self.ready = True
            print("faster-whisper ASR model loaded successfully.")
        except Exception as e:
            print(f"Failed to load faster-whisper ASR model: {e}")
            raise

    def _load_openvino(self, model_dir: str, device: str):
        import openvino as ov

        model_path = Path(model_dir)
        ov_dir = model_path / "qwen3_asr_int8"

        if not ov_dir.exists():
            raise FileNotFoundError(f"ASR model directory not found at {ov_dir}")

        print(f"Loading ASR model from {ov_dir} on {device}...")

        # Initialize OpenVINO Core
        core = ov.Core()

        # Load and compile models
        try:
            self.audio_enc = core.compile_model(str(ov_dir / "audio_encoder_model.xml"), device)
            self.embedder = core.compile_model(str(ov_dir / "thinker_embeddings_model.xml"), device)
            dec_comp = core.compile_model(str(ov_dir / "decoder_model.xml"), device)
            self.dec_req = dec_comp.create_infer_request()

            # Load Processor
            self.processor = LightProcessor(ov_dir)
            self.pad_id = self.processor.pad_id
            self.ready = True
            print("OpenVINO ASR model loaded successfully.")
        except Exception as e:
            print(f"Failed to load OpenVINO ASR model: {e}")
            raise

    def transcribe(self, audio: np.ndarray, max_tokens: int = 300, language: str | None = None, context: str | None = None) -> str:
        """
        Transcribe 16kHz float32 audio, delegating to the active engine.
        """
        if not self.ready:
            raise RuntimeError("ASR Engine not loaded.")

        with self._lock:
            if self.is_cpu:
                return self._transcribe_openvino(audio, max_tokens, language, context)
            else:
                return self._transcribe_faster_whisper(audio, language)

    def _transcribe_faster_whisper(self, audio: np.ndarray, language: str | None) -> str:
        import traceback
        try:
            print(f"[FW] audio shape={audio.shape}, dtype={audio.dtype}, lang={language}")
            segments, info = self.fw_model.transcribe(
                audio,
                language=language,      # ISO 639-1: "ja", "en", etc.
                beam_size=5,
                vad_filter=False,       # 我們已有自己的 VAD pipeline
                condition_on_previous_text=False,
            )
            print(f"[FW] detected language: {info.language} (prob={info.language_probability:.2f})")
            seg_list = list(segments)  # 強制消費 generator
            print(f"[FW] segments count: {len(seg_list)}")
            text = " ".join(seg.text for seg in seg_list).strip()
            print(f"[FW] raw text: {repr(text)}")
            return text
        except Exception as e:
            print(f"faster-whisper transcription error: {e}")
            traceback.print_exc()
            return ""

    def _transcribe_openvino(self, audio: np.ndarray, max_tokens: int, language: str | None, context: str | None) -> str:
        # 1. Preprocess using LightProcessor
        mel, ids = self.processor.prepare(audio, language=language, context=context)

        # 2. Audio encoding + Text Embedding
        ae_out = self.audio_enc({"mel": mel})
        ae = list(ae_out.values())[0]

        te_out = self.embedder({"input_ids": ids})
        te = list(te_out.values())[0]

        # 3. Combine audio features into audio pad positions
        combined = te.copy()
        mask = ids[0] == self.pad_id
        n_pad = int(mask.sum())
        n_ae = ae.shape[1]

        if n_pad != n_ae:
            mn = min(n_pad, n_ae)
            combined[0, np.where(mask)[0][:mn]] = ae[0, :mn]
        else:
            combined[0, mask] = ae[0]

        # 4. Global auto-regressive decoding
        L = combined.shape[1]
        pos = np.arange(L, dtype=np.int64)[np.newaxis, :]

        self.dec_req.reset_state()
        out = self.dec_req.infer({0: combined, "position_ids": pos})
        logits = list(out.values())[0]

        eos = self.processor.eos_id
        eot = self.processor.eot_id

        gen = []
        nxt = int(np.argmax(logits[0, -1, :]))
        cur = L

        while nxt not in (eos, eot) and len(gen) < max_tokens:
            gen.append(nxt)
            # Next token embedding
            emb_out = self.embedder({"input_ids": np.array([[nxt]], dtype=np.int64)})
            emb = list(emb_out.values())[0]

            # Single step decode
            out = self.dec_req.infer({0: emb, "position_ids": np.array([[cur]], dtype=np.int64)})
            logits = list(out.values())[0]
            nxt = int(np.argmax(logits[0, -1, :]))
            cur += 1

        # 5. Decode tokens to text
        raw = self.processor.decode(gen)

        if "<asr_text>" in raw:
            raw = raw.split("<asr_text>", 1)[1]
        return raw.strip()
