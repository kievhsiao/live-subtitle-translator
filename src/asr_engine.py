import numpy as np
import openvino as ov
import threading
import os
from pathlib import Path
from src.processor_numpy import LightProcessor

class ASREngine:
    """ASR Engine using OpenVINO for Qwen3-ASR-0.6B."""
    
    def __init__(self):
        self.ready = False
        self._lock = threading.Lock()
        self.audio_enc = None
        self.embedder = None
        self.dec_req = None
        self.processor = None
        self.pad_id = None

    def load(self, model_dir: str, device: str = "CPU"):
        """
        Load models from model_dir/qwen3_asr_int8.
        device can be "CPU", "GPU", "AUTO", etc.
        """
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
            print("ASR model loaded successfully.")
        except Exception as e:
            print(f"Failed to load ASR model: {e}")
            raise

    def transcribe(self, audio: np.ndarray, max_tokens: int = 300, language: str | None = None, context: str | None = None) -> str:
        """
        Transcribe 16kHz float32 audio.
        """
        if not self.ready:
            raise RuntimeError("ASR Engine not loaded.")
            
        with self._lock:
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
                
            print(f"DEBUG - Generated tokens: {gen}")
            
            # 5. Decode tokens to text
            raw = self.processor.decode(gen)
            print(f"DEBUG - Raw decoded string: {repr(raw)}")
            
            if "<asr_text>" in raw:
                raw = raw.split("<asr_text>", 1)[1]
            return raw.strip()

if __name__ == "__main__":
    # Example usage (test)
    engine = ASREngine()
    print("ASR Engine initialized.")
