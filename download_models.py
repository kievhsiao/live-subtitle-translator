import os
import urllib.request
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
MODEL_DIR_CPU = BASE_DIR / "models" / "cpu"
MODEL_DIR_VAD = BASE_DIR / "models" / "vad"
MODEL_DIR_COMMON = BASE_DIR / "models" / "common"
ASR_DIR = MODEL_DIR_CPU / "qwen3_asr_int8"

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

MEL_FILTER_URL = f"{HF_BASE}/mel_filters.npy"

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

def download_vad():
    print("=== Downloading Shared VAD Model ===")
    vad_path = MODEL_DIR_VAD / "silero_vad_v4.onnx"
    download_file(VAD_URL, vad_path)
    
def download_common():
    print("=== Downloading Shared Common Files ===")
    mel_path = MODEL_DIR_COMMON / "mel_filters.npy"
    download_file(MEL_FILTER_URL, mel_path)
    
def download_cpu():
    print("=== Downloading CPU Models (OpenVINO) ===")
    
    # Download ASR Files
    for filename, url in REQUIRED_FILES:
        dest = ASR_DIR / filename
        download_file(url, dest)
        
    print("\n--- CPU Models verification finished ---")
    print("If mel_filters.npy is missing, please copy it from QwenASRMiniTool.")

def download_gpu():
    print("\n=== Downloading GPU Models (faster-whisper / CTranslate2) ===")
    try:
        from huggingface_hub import snapshot_download
        local_model_dir = Path("models/gpu/faster-whisper-large-v3")
        
        if not local_model_dir.exists():
            print("Downloading faster-whisper-large-v3 to local GPU directory (This may take a while, ~3GB)...")
            local_model_dir.parent.mkdir(parents=True, exist_ok=True)
            snapshot_download(
                repo_id="Systran/faster-whisper-large-v3",
                local_dir=str(local_model_dir),
                local_dir_use_symlinks=False,
                resume_download=True
            )
            print(f"Finished downloading GPU model to {local_model_dir}")
        else:
            print(f"GPU Model already exists at {local_model_dir}, skipping download.")
            
    except ImportError:
        print("huggingface_hub not installed. Skipping GPU model pre-download. (It will auto-download when running the app if needed)")
    except Exception as e:
        print(f"Failed to check/download GPU models: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download models for Live Subtitle Translator.")
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["cpu", "gpu", "all"], 
        default="gpu",
        help="Choose which models to download: 'cpu', 'gpu', or 'all'. Defaults to 'gpu'."
    )
    args = parser.parse_args()
    
    print(f"=== Model Downloader (Mode: {args.mode.upper()}) ===")
    
    # VAD and Common files are shared across all modes
    download_vad()
    download_common()
    
    if args.mode in ["cpu", "all"]:
        download_cpu()
        
    if args.mode in ["gpu", "all"]:
        download_gpu()
        
    print("\nAll requested downloads finished.")

if __name__ == "__main__":
    main()
