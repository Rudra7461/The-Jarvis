from collections import deque
import io
import re
from typing import Callable
import winsound

import numpy as np
from scipy.io import wavfile
import sounddevice as sd
import speech_recognition as sr


StateCallback = Callable[[str, str | None], None]
WakeGreetCallback = Callable[[str], None]


class JarvisEars:
    """
    Conversational VAD listener:
    - Starts in SLEEP mode ('IDLE') waiting for 'Hey Jarvis' / 'Jarvis'.
    - Once woken up, stays in ACTIVE continuous conversation mode until 'Bye Jarvis'.
    - Uses sounddevice (int16 @ 16kHz) + scipy + SpeechRecognition (zero PyAudio).
    """

    SLEEP_TRIGGERS = (
        "bye jarvis",
        "goodbye jarvis",
        "good bye jarvis",
        "sleep jarvis",
        "go to sleep",
        "stop listening",
        "that's all jarvis",
        "thats all jarvis",
    )

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration: float = 0.1,
        silence_timeout: float = 1.2,
        max_record_seconds: float = 15.0,
        wake_word: str = "jarvis",
        energy_multiplier: float = 2.2,
        min_threshold: float = 280.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_samples = int(self.sample_rate * self.chunk_duration)

        self.max_silent_chunks = int(round(silence_timeout / chunk_duration))
        self.max_record_chunks = int(round(max_record_seconds / chunk_duration))

        self.wake_word = wake_word.lower().strip()
        self.is_awake = False  # Starts asleep until 'Hey Jarvis' is spoken once
        self.energy_multiplier = energy_multiplier
        self.min_threshold = min_threshold
        self.threshold = min_threshold

        self.recognizer = sr.Recognizer()
        self._wake_strip_pattern = re.compile(
            rf"\b(?:hey\s+|hello\s+|hi\s+|ok\s+|okay\s+|wake\s+up\s+)?{re.escape(self.wake_word)}\b[\s,.:;!?]*",
            flags=re.IGNORECASE,
        )

    @staticmethod
    def _compute_rms(audio_chunk: np.ndarray) -> float:
        samples = audio_chunk.astype(np.float64)
        return float(np.sqrt(np.mean(samples * samples)))

    @staticmethod
    def _play_activation_chime() -> None:
        try:
            winsound.Beep(880, 60)
            winsound.Beep(1320, 80)
        except Exception:
            pass

    def set_awake(self, awake: bool) -> None:
        self.is_awake = bool(awake)
        print(f"[EARS] Session Awake State: {self.is_awake}")

    @classmethod
    def is_sleep_command(cls, text: str) -> bool:
        cleaned = re.sub(r"[^\w\s']", "", text.lower()).strip()
        return any(trigger in cleaned for trigger in cls.SLEEP_TRIGGERS)

    def calibrate_ambient_noise(self, duration: float = 0.5) -> float:
        """Sample room noise for 0.5s on startup to lock the dynamic VAD threshold."""
        calibration_chunks = max(1, int(round(duration / self.chunk_duration)))
        rms_readings: list[float] = []

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.chunk_samples,
        ) as stream:
            stream.read(self.chunk_samples)
            for _ in range(calibration_chunks):
                data, _ = stream.read(self.chunk_samples)
                rms_readings.append(self._compute_rms(data))

        ambient_rms = float(np.mean(rms_readings)) if rms_readings else 0.0
        self.threshold = max(self.min_threshold, ambient_rms * self.energy_multiplier)
        print(f"[EARS] Ambient RMS: {ambient_rms:.1f} | VAD Threshold: {self.threshold:.1f}")
        return self.threshold

    def record_phrase(self, on_speech_start: Callable[[], None] | None = None) -> np.ndarray:
        """Buffer 0.1s chunks once voice crosses RMS threshold; stop after 1.2s of silence."""
        pre_roll: deque[np.ndarray] = deque(maxlen=3)
        recorded_chunks: list[np.ndarray] = []

        is_recording = False
        silent_chunks = 0

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.chunk_samples,
        ) as stream:
            while True:
                data, _ = stream.read(self.chunk_samples)
                chunk = data.copy().reshape(-1)
                rms = self._compute_rms(chunk)

                if not is_recording:
                    if rms > self.threshold:
                        is_recording = True
                        if on_speech_start is not None:
                            on_speech_start()
                        recorded_chunks.extend(pre_roll)
                        recorded_chunks.append(chunk)
                        silent_chunks = 0
                    else:
                        pre_roll.append(chunk)
                else:
                    recorded_chunks.append(chunk)
                    if rms <= self.threshold:
                        silent_chunks += 1
                    else:
                        silent_chunks = 0

                    if silent_chunks >= self.max_silent_chunks or len(recorded_chunks) >= self.max_record_chunks:
                        break

        return np.concatenate(recorded_chunks)

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Convert int16 numpy audio buffer into text via Google Speech Recognition."""
        if audio_data.size == 0:
            return ""

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, self.sample_rate, audio_data)
        wav_buffer.seek(0)

        with sr.AudioFile(wav_buffer) as source:
            audio = self.recognizer.record(source)

        try:
            text = self.recognizer.recognize_google(audio)
            return text.strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as exc:
            print(f"[EARS] Speech API network error: {exc}")
            return ""

    def listen(
        self,
        on_state_change: StateCallback | None = None,
        on_wake_greet: WakeGreetCallback | None = None,
    ) -> str:
        """
        1. If sleeping (is_awake == False): Wait passively in IDLE until 'Hey Jarvis' is heard,
           wake up into an active conversation session, speak 'At your service, Sir.', and
           begin continuous conversation.
        2. If awake (is_awake == True): Capture every spoken sentence directly without needing
           the wake word again until Rudra says 'Bye Jarvis'.
        """
        if not self.is_awake:
            if on_state_change:
                on_state_change("IDLE", "STANDBY // SAY 'HEY JARVIS'")

            while not self.is_awake:
                passive_audio = self.record_phrase()
                heard = self.transcribe(passive_audio)
                if not heard:
                    continue

                print(f"[EARS - SLEEPING] Heard: '{heard}'")
                lower_heard = heard.lower()

                if self.wake_word in lower_heard:
                    self.is_awake = True
                    inline_command = self._wake_strip_pattern.sub(" ", heard).strip()
                    inline_command = re.sub(r"\s+", " ", inline_command).strip(" ,.!?")

                    # If Rudra said "Hey Jarvis, how was your day?" in one breath, answer directly
                    if len(inline_command.split()) >= 2:
                        self._play_activation_chime()
                        if on_state_change:
                            on_state_change("THINKING", "NEURAL CORE // PROCESSING...")
                        return inline_command

                    greet_line = (
                        "Hello Sir, at your service Sir."
                        if "hello" in lower_heard
                        else "At your service, Sir."
                    )
                    if on_wake_greet is not None:
                        on_wake_greet(greet_line)
                    else:
                        self._play_activation_chime()
                    break

        # Active conversation session: listen immediately with no wake word needed
        if on_state_change:
            on_state_change("LISTENING", "LISTENING // SPEAK FREELY")

        command_audio = self.record_phrase()

        if on_state_change:
            on_state_change("THINKING", "NEURAL CORE // POLISHING...")

        return self.transcribe(command_audio)