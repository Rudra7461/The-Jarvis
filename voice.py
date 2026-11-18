import asyncio
import os
import re
import tempfile
from typing import Any

import edge_tts
import sounddevice as sd
import soundfile as sf

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


VOICE_NAME = "en-GB-RyanNeural"
VOICE_RATE = "+3%"
VOICE_PITCH = "-2Hz"


_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MARKDOWN_SYMBOLS_RE = re.compile(r"[*#`~>_|\[\]]+")
_BULLET_DASH_RE = re.compile(r"(^|\s)-+(\s|$)")
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)
_WHITESPACE_RE = re.compile(r"\s+")


def sanitize_for_speech(text: str) -> str:
    """Strip all Markdown tokens, links, and emojis before TTS synthesis."""
    if not text:
        return ""

    cleaned = _MARKDOWN_LINK_RE.sub(r"\1", text)
    cleaned = _EMOJI_RE.sub("", cleaned)
    cleaned = _MARKDOWN_SYMBOLS_RE.sub("", cleaned)
    cleaned = _BULLET_DASH_RE.sub(" ", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


async def _synthesize_edge_tts(text: str, output_path: str) -> None:
    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE_NAME,
        rate=VOICE_RATE,
        pitch=VOICE_PITCH,
    )
    await communicate.save(output_path)


def _run_coroutine(coro: Any) -> None:
    try:
        asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()


def _speak_offline_fallback(clean_text: str) -> None:
    """Offline Windows SAPI5 fallback so J.A.R.V.I.S. keeps speaking if Wi-Fi drops."""
    if pyttsx3 is None:
        print(f"[VOICE - OFFLINE] {clean_text}")
        return

    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 185)

        for voice in engine.getProperty("voices"):
            if any(tag in voice.name.lower() or tag in voice.id.lower() for tag in ("hazel", "george", "en-gb")):
                engine.setProperty("voice", voice.id)
                break

        engine.say(clean_text)
        engine.runAndWait()
        engine.stop()
    except Exception as exc:
        print(f"[VOICE - FALLBACK ERROR] {exc} | {clean_text}")


def speak(text: str, ui: Any = None, next_state: str = "IDLE") -> None:
    """
    Sanitize text, synthesize British neural voice (en-GB-RyanNeural), set HUD to SPEAKING,
    play audio via sounddevice + soundfile, delete temp file, and transition HUD to next_state.
    """
    clean_text = sanitize_for_speech(text)
    if not clean_text:
        if ui is not None:
            ui.set_state(next_state)
        return

    tmp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = tmp_file.name
    tmp_file.close()

    try:
        _run_coroutine(_synthesize_edge_tts(clean_text, tmp_path))

        if ui is not None:
            ui.set_state("SPEAKING", "J.A.R.V.I.S. // SPEAKING")

        audio_data, sample_rate = sf.read(tmp_path, dtype="float32")
        sd.play(audio_data, sample_rate)
        sd.wait()

    except Exception as exc:
        print(f"[VOICE] Edge TTS offline ({exc.__class__.__name__}), using offline fallback.")
        if ui is not None:
            ui.set_state("SPEAKING", "J.A.R.V.I.S. // SPEAKING")
        _speak_offline_fallback(clean_text)

    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        if ui is not None:
            ui.set_state(next_state)