"""Pure Python audio recording using sounddevice."""

import threading
import time
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import numpy as np

from ..config.settings import Settings


class AudioRecorder:
    """Python audio recording using sounddevice."""

    def __init__(self, settings: Optional[Settings] = None, device_index: Optional[int] = None):
        self.settings = settings or Settings()
        self.device_index = device_index
        self.is_recording = False
        self.recording_thread = None
        self.start_time = None
        self.output_file = None
        self.audio_data = []
        self.sample_rate = 44100  # CD quality
        self.channels = 1  # Mono

        # Try to import sounddevice
        try:
            import sounddevice as sd
            self.sd = sd
            self._check_device()
        except ImportError:
            raise ImportError(
                "sounddevice library is required for Python audio recording. "
                "Install it with: pip install sounddevice"
            )

    def _check_device(self):
        """Check if the specified device is available."""
        if self.device_index is not None:
            try:
                devices = self.sd.query_devices()
                if self.device_index >= len(devices):
                    print(f"Warning: Device index {self.device_index} not found. Using default device.")
                    self.device_index = None
            except Exception as e:
                print(f"Warning: Could not query devices: {e}. Using default device.")
                self.device_index = None

    def _ensure_unique_filename(self, base_path: Path) -> Path:
        """Ensure the filename is unique by adding a counter if necessary."""
        if not base_path.exists():
            return base_path

        # Extract name and extension
        stem = base_path.stem  # filename without extension
        suffix = base_path.suffix  # .wav
        parent = base_path.parent

        # Try adding numbers until we find a unique name
        counter = 1
        while True:
            new_name = f"{stem}_{counter:02d}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1

            # Safety check to avoid infinite loop
            if counter > 999:
                # Fallback to timestamp if we somehow hit 999 files
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                return parent / f"{stem}_{timestamp}{suffix}"

    @classmethod
    def list_devices(cls) -> List[Dict[str, Any]]:
        """List available audio input devices."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = []

            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append({
                        'index': i,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'sample_rate': device['default_samplerate']
                    })

            return input_devices
        except ImportError:
            return []
        except Exception as e:
            print(f"Error listing devices: {e}")
            return []

    def start_recording(self, filename: Optional[str] = None) -> bool:
        """Start recording audio using sounddevice."""
        if self.is_recording:
            return False

        try:
            # Set up output filename
            if filename:
                filename = filename if filename.endswith(".wav") else f"{filename}.wav"
                base_path = self.settings.meetings_dir / filename

                # Ensure unique filename by adding counter if file exists
                self.output_file = self._ensure_unique_filename(base_path)
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                self.output_file = self.settings.meetings_dir / f"recording_{timestamp}.wav"

            # Ensure output directory exists
            self.output_file.parent.mkdir(parents=True, exist_ok=True)

            # Reset audio data
            self.audio_data = []
            self.is_recording = True
            self.start_time = time.time()

            # Start recording in a separate thread
            self.recording_thread = threading.Thread(target=self._record_audio)
            self.recording_thread.daemon = True
            self.recording_thread.start()

            return True

        except Exception as e:
            print(f"Error starting recording: {e}")
            self.is_recording = False
            return False

    def _record_audio(self):
        """Internal method to record audio in a separate thread."""
        try:
            # Use callback-based recording for smooth, continuous audio
            self.audio_data = []

            def audio_callback(indata, frames, time, status):
                """Callback function for continuous audio recording."""
                if status:
                    print(f"Audio callback status: {status}")
                if self.is_recording:
                    # Copy the audio data to avoid buffer issues
                    self.audio_data.append(indata.copy())

            # Start the input stream with callback
            with self.sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=self.device_index,
                dtype='float32',
                callback=audio_callback,
                blocksize=1024,  # Small block size for low latency
            ):
                # Keep recording until stopped
                while self.is_recording:
                    self.sd.sleep(100)  # Sleep 100ms between checks

        except Exception as e:
            print(f"Error during recording: {e}")
            self.is_recording = False

    def stop_recording(self) -> Optional[str]:
        """Stop recording and save the audio file."""
        if not self.is_recording:
            return None

        self.is_recording = False

        # Wait for recording thread to finish
        if self.recording_thread:
            self.recording_thread.join(timeout=5.0)  # Increased timeout

        try:
            # Combine all audio data
            if self.audio_data:
                # Concatenate all audio chunks
                audio_array = np.concatenate(self.audio_data, axis=0)

                # Ensure we have the correct shape (samples, channels) or (samples,) for mono
                if audio_array.ndim == 1:
                    # Already mono
                    pass
                elif audio_array.ndim == 2 and audio_array.shape[1] == 1:
                    # Convert (samples, 1) to (samples,) for mono
                    audio_array = audio_array.flatten()
                elif audio_array.ndim == 2 and audio_array.shape[1] > 1:
                    # Convert multi-channel to mono by averaging
                    audio_array = np.mean(audio_array, axis=1)

                # Normalize audio to prevent clipping
                max_val = np.max(np.abs(audio_array))
                if max_val > 0:
                    audio_array = audio_array / max_val * 0.95  # Leave some headroom

                # Save as WAV file using soundfile for better quality
                try:
                    import soundfile as sf
                    sf.write(str(self.output_file), audio_array, self.sample_rate, subtype='PCM_16')
                    print(f"Recording saved to: {self.output_file} (using soundfile)")
                except ImportError:
                    # Fallback to wave module
                    with wave.open(str(self.output_file), 'wb') as wf:
                        wf.setnchannels(self.channels)
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(self.sample_rate)

                        # Convert to 16-bit integers with proper scaling
                        audio_int16 = (audio_array * 32767).astype(np.int16)
                        wf.writeframes(audio_int16.tobytes())
                    print(f"Recording saved to: {self.output_file} (using wave)")

                return str(self.output_file)
            else:
                print("No audio data recorded")
                return None

        except Exception as e:
            print(f"Error saving recording: {e}")
            import traceback
            traceback.print_exc()
            return None

    def is_recording_active(self) -> bool:
        """Check if recording is currently active."""
        return self.is_recording

    def get_recording_duration(self) -> float:
        """Get the current recording duration in seconds."""
        if self.start_time and self.is_recording:
            return time.time() - self.start_time
        return 0.0
