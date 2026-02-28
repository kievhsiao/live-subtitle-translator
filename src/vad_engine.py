import numpy as np
import onnxruntime as ort
import os

class VADEngine:
    def __init__(self, model_path=None, threshold=0.5, sample_rate=16000):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.chunk_size = 512  # Silero VAD v4 requires 512 samples for 16kHz
        
        if model_path is None:
            # Look for model in default locations
            model_path = os.path.join("models", "vad", "silero_vad_v4.onnx")
            
        if not os.path.exists(model_path):
            print(f"VAD model not found at {model_path}. Please ensure it exists.")
            self.session = None
        else:
            self.session = ort.InferenceSession(
                model_path, providers=["CPUExecutionProvider"]
            )
        
        self.reset_state()

    def reset_state(self):
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)

    def is_speech(self, audio_chunk):
        """
        Check if the audio chunk contains speech.
        audio_chunk should be 512 samples at 16kHz float32.
        """
        if self.session is None:
            return False
            
        if len(audio_chunk) != self.chunk_size:
            # Pad or truncate to 512
            if len(audio_chunk) < self.chunk_size:
                audio_chunk = np.pad(audio_chunk, (0, self.chunk_size - len(audio_chunk)))
            else:
                audio_chunk = audio_chunk[:self.chunk_size]
                
        # Prep input
        input_data = audio_chunk[np.newaxis, :].astype(np.float32)
        sr = np.array(self.sample_rate, dtype=np.int64)
        
        # Inference
        out, self._h, self._c = self.session.run(
            None, 
            {"input": input_data, "h": self._h, "c": self._c, "sr": sr}
        )
        
        prob = float(out[0, 0])
        return prob >= self.threshold, prob

if __name__ == "__main__":
    # Test VAD
    vad = VADEngine()
    print("VAD initialized.")
