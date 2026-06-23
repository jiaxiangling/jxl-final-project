# -*- coding: utf-8 -*-
"""语音服务：Whisper STT + OpenAI TTS + 离线降级。"""

import io
from abc import ABC, abstractmethod
from typing import Optional

from config import get_settings, is_online


class SpeechService(ABC):
    """语音服务抽象接口。"""

    @property
    @abstractmethod
    def available(self) -> bool:
        ...

    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> str:
        """语音转文字（STT）。"""
        ...

    @abstractmethod
    def synthesize(self, text: str, voice: str = "alloy", speed: float = 1.0) -> Optional[bytes]:
        """文字转语音（TTS），返回 mp3 bytes。"""
        ...


class OpenAISpeech(SpeechService):
    """OpenAI Whisper + TTS 实现。"""

    def __init__(self) -> None:
        from openai import OpenAI
        settings = get_settings()
        self._client = OpenAI(api_key=settings.api_key)
        self._stt_model = settings.stt_model
        self._tts_model = settings.tts_model

    @property
    def available(self) -> bool:
        return True

    def transcribe(self, audio_bytes: bytes) -> str:
        """使用 Whisper 将语音转写为文字。"""
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "recording.webm"
        response = self._client.audio.transcriptions.create(
            model=self._stt_model,
            file=audio_file,
        )
        return response.text.strip()

    def synthesize(self, text: str, voice: str = "alloy", speed: float = 1.0) -> Optional[bytes]:
        """使用 OpenAI TTS 将文字合成为语音。"""
        # 限制文本长度，避免超长
        text = text[:3000]
        response = self._client.audio.speech.create(
            model=self._tts_model,
            voice=voice,
            input=text,
            speed=speed,
        )
        return response.content


class MockSpeech(SpeechService):
    """离线降级：语音不可用。"""

    @property
    def available(self) -> bool:
        return False

    def transcribe(self, audio_bytes: bytes) -> str:
        raise RuntimeError("语音转写不可用：需要 OPENAI_API_KEY。请使用文本输入。")

    def synthesize(self, text: str, voice: str = "alloy", speed: float = 1.0) -> Optional[bytes]:
        return None


def get_speech() -> SpeechService:
    """根据模式返回语音服务实例。"""
    if is_online():
        try:
            return OpenAISpeech()
        except Exception:
            return MockSpeech()
    return MockSpeech()
