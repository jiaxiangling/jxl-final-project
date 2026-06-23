# -*- coding: utf-8 -*-
"""全局配置：模型、路径、CEFR 常量、模式探测。"""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# ── 路径 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
TOOLS_DATA_DIR = os.path.join(BASE_DIR, "tools", "data")

# ── CEFR 常量 ─────────────────────────────────────────
CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
CEFR_NUMERIC = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
NUMERIC_CEFR = {v: k for k, v in CEFR_NUMERIC.items()}

L1_SUPPORTED = ["zh", "es"]
L1_LABELS = {"zh": "中文", "es": "西班牙语(墨西哥)"}

# ── 模型与 API ────────────────────────────────────────
LLM_MODEL = "gpt-4o"
STT_MODEL = "whisper-1"
TTS_MODEL = "tts-1"

# ── Agent 参数 ────────────────────────────────────────
MAX_TOOL_ITERS = 5          # 单轮 ReAct 循环最大工具迭代次数
MAX_AUDIO_SECONDS = 60      # 单次录音上限（秒）
NO_TOOL_NUDGE_THRESHOLD = 3  # 连续 N 轮无工具调用则注入提示
HISTORY_WINDOW = 12         # 保留最近 N 轮对话历史喂给 LLM


class Settings:
    """运行时设置（可在 UI 中覆盖）。"""

    def __init__(self) -> None:
        self.api_key: Optional[str] = os.getenv("OPENAI_API_KEY", "").strip() or None
        self.tts_voice: str = os.getenv("TTS_VOICE", "alloy")
        self.tts_speed: float = float(os.getenv("TTS_SPEED", "1.0"))
        self.llm_model: str = LLM_MODEL
        self.stt_model: str = STT_MODEL
        self.tts_model: str = TTS_MODEL
        self.max_tool_iters: int = MAX_TOOL_ITERS

    @property
    def mode(self) -> str:
        """返回 'online' 或 'offline'。"""
        return "online" if self.api_key else "offline"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def is_online() -> bool:
    return get_settings().mode == "online"


def ensure_dirs() -> None:
    """确保运行时目录存在。"""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
