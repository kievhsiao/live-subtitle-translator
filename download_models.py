import os
import urllib.request
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "ov_models"
ASR_DIR = MODEL_DIR / "qwen3_asr_int8"

# URLs
HF_BASE = "https://huggingface.co/dseditor/Qwen3-ASR-0.6B-INT8_ASYM-OpenVINO/resolve/main"
VAD_URL = "https://github.com/snakers4/silero-vad/raw/v4.0/files/silero_vad.onnx"

REQUIRED_FILES = [
    ("audio_encoder_model.bin", f"{HF_BASE}/audio_encoder_model.bin"),
    ("audio_encoder_model.xml", f"{HF_BASE}/audio_encoder_model.xml"),
    ("decoder_model.bin", f"{HF_BASE}/decoder_model.bin"),
    ("decoder_model.xml", f"{HF_BASE}/decoder_model.xml"),
    ("thinker_embeddings_model.bin", f"{HF_BASE}/thinker_embeddings_model.bin"),
    ("thinker_embeddings_model.xml", f"{HF_BASE}/thinker_embeddings_model.xml"),
    ("config.json", f"{HF_BASE}/config.json"),
    ("preprocessor_config.json", f"{HF_BASE}/preprocessor_config.json"),
    ("tokenizer_config.json", f"{HF_BASE}/tokenizer_config.json"),
    ("vocab.json", f"{HF_BASE}/vocab.json"),
    ("merges.txt", f"{HF_BASE}/merges.txt"),
    ("prompt_template.json", f"{HF_BASE}/prompt_template.json"),
]

def download_file(url, dest):
    if dest.exists():
        print(f"Skipping {dest.name} (already exists)")
        return
    
    print(f"Downloading {dest.name}...")
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Simple download with progress placeholder
        urllib.request.urlretrieve(url, dest)
        print(f"Finished {dest.name}")
    except Exception as e:
        print(f"Failed to download {dest.name}: {e}")

def main():
    print("=== Model Downloader ===")
    
    # Download VAD
    vad_path = MODEL_DIR / "silero_vad_v4.onnx"
    download_file(VAD_URL, vad_path)
    
    # Download ASR Files
    for filename, url in REQUIRED_FILES:
        dest = ASR_DIR / filename
        download_file(url, dest)
        
    # Copy mel_filters.npy if it exists in parent or source
    # (In QwenASRMiniTool it was generated or manually placed)
    # We'll expect it to be handled or the user to copy it.
    
    print("\nDownload process finished. If mel_filters.npy is missing, please copy it from QwenASRMiniTool.")

if __name__ == "__main__":
    main()
