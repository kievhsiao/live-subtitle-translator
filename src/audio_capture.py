import pyaudiowpatch as pyaudio
import numpy as np
import threading
import queue
import time

class AudioCapture:
    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio_queue = queue.Queue()
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.is_running = False
        self._thread = None
        self.actual_rate = None # To be set on start
        self.channels = None    # To be set on start
        self.wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
        self.default_device_index = None
        self._find_default_loopback_device()

    def _find_default_loopback_device(self):
        """Find the default loopback device for WASAPI."""
        default_speakers = self.p.get_device_info_by_index(self.wasapi_info["defaultOutputDevice"])
        
        if not default_speakers["isLoopbackDevice"]:
            for loopback in self.p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    self.default_device_index = loopback["index"]
                    break
        else:
            self.default_device_index = default_speakers["index"]
            
        if self.default_device_index is None:
            # Fallback: find any loopback device
            for loopback in self.p.get_loopback_device_info_generator():
                self.default_device_index = loopback["index"]
                break

    def start(self, device_index=None):
        if self.is_running:
            return
            
        if device_index is None:
            device_index = self.default_device_index
            
        if device_index is None:
            raise RuntimeError("No loopback device found.")

        device_info = self.p.get_device_info_by_index(device_index)
        self.actual_rate = int(device_info["defaultSampleRate"])
        self.channels = device_info["maxInputChannels"]
        
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.actual_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._callback
        )
        
        self.is_running = True
        self.stream.start_stream()
        print(f"Audio capture started on device: {device_info['name']} at {self.actual_rate}Hz")

    def _callback(self, in_data, frame_count, time_info, status):
        # Convert stereo/multi-channel to mono and resample to 16kHz if necessary
        # For simplicity, we'll assume the ASR handles raw data or we handle it here.
        # But for Qwen-ASR, 16kHz Mono is best.
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def stop(self):
        self.is_running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        print("Audio capture stopped.")

    def get_audio_chunk(self):
        try:
            return self.audio_queue.get(timeout=0.1)
        except queue.Empty:
            return None

if __name__ == "__main__":
    # Test capture
    capture = AudioCapture()
    try:
        capture.start()
        print("Capturing for 5 seconds...")
        time.sleep(5)
    finally:
        capture.stop()
