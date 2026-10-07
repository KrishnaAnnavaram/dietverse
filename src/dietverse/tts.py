"""Text-to-speech behind one interface. Each answer gets its own audio file (no shared 'audio.mp3')."""

from __future__ import annotations

import math
import struct
import uuid
import wave
from pathlib import Path
from typing import Protocol


class TTSError(RuntimeError):
    pass


class Speech(Protocol):
    def synthesize(self, text: str) -> Path | None: ...


class NoSpeech:
    def synthesize(self, text: str) -> Path | None:
        return None


class OfflineTone:
    """Offline stand-in: a short WAV tone whose length grows with the text. It tests the audio path only."""

    def __init__(self, audio_dir: Path):
        self.audio_dir = Path(audio_dir)

    def synthesize(self, text: str) -> Path:
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        path = self.audio_dir / f"{uuid.uuid4().hex}.wav"
        rate, seconds = 8000, min(5.0, 0.2 + 0.02 * len(text.split()))
        frames = b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 440 * i / rate)))
                          for i in range(int(rate * seconds)))
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(frames)
        return path


class PollySpeech:  # pragma: no cover - needs the "aws" extra and AWS credentials in the backend environment
    """Amazon Polly neural voice. boto3 reads the credentials from the environment or an IAM role."""

    def __init__(self, audio_dir: Path, voice: str):
        try:
            import boto3
        except ImportError as exc:
            raise TTSError("install the extra: pip install 'dietverse[aws]'") from exc
        self.client = boto3.client("polly")
        self.audio_dir, self.voice = Path(audio_dir), voice

    def synthesize(self, text: str) -> Path:
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        resp = self.client.synthesize_speech(Text=text[:2900], OutputFormat="mp3", VoiceId=self.voice, Engine="neural")
        path = self.audio_dir / f"{uuid.uuid4().hex}.mp3"
        path.write_bytes(resp["AudioStream"].read())
        return path


def build_speech(provider: str, audio_dir: Path, voice: str) -> Speech:
    if provider == "none":
        return NoSpeech()
    if provider == "offline":
        return OfflineTone(audio_dir)
    if provider == "polly":
        return PollySpeech(audio_dir, voice)
    raise TTSError(f"unknown TTS provider {provider!r}")
